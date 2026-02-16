from dataclasses import dataclass
import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import decrypt_text, encrypt_text
from app.models.log import OperationLog
from app.repositories.system_config_repository import SystemConfigRepository
from app.schemas.system_config import (
    ClaimContactResponse,
    StorageChannelItem,
    StorageChannelsResponse,
    StorageChannelsUpdateRequest,
    StorageChannelTestRequest,
    StorageConfigResponse,
    StorageConfigTestRequest,
    StorageConfigUpdateRequest,
)
from app.storage.aliyun_oss_storage import AliyunOssStorage
from app.storage.local_storage import LocalFileStorage
from app.storage.minio_storage import MinioStorage

SECRET_KEYS = {
    "minio_access_key",
    "minio_secret_key",
    "aliyun_oss_access_key_id",
    "aliyun_oss_access_key_secret",
}

STRIP_KEYS = {
    "provider",
    "bucket",
    "base_url",
    "storage_prefix",
    "local_storage_dir",
    "minio_endpoint",
    "minio_access_key",
    "minio_secret_key",
    "aliyun_oss_endpoint",
    "aliyun_oss_region",
    "aliyun_oss_access_key_id",
    "aliyun_oss_access_key_secret",
}

CLAIM_CONTACT_KEY = "claim_contact_text"
DEFAULT_CLAIM_CONTACT = "当前礼物未到达激活时间、已兑换或者失效，请联系xxxxxxxxxxx"
STORAGE_CHANNELS_KEY = "storage_channels_v1"


@dataclass
class StorageRuntimeConfig:
    provider: str
    bucket: str
    base_url: str
    storage_prefix: str
    local_storage_dir: str
    minio_endpoint: str
    minio_secure: bool
    minio_access_key: str
    minio_secret_key: str
    aliyun_oss_endpoint: str
    aliyun_oss_region: str
    aliyun_oss_access_key_id: str
    aliyun_oss_access_key_secret: str


class SystemConfigService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SystemConfigRepository(db)

    def get_storage_config(self) -> StorageConfigResponse:
        runtime = self._resolve_runtime_config()
        return StorageConfigResponse(
            provider=runtime.provider,
            bucket=runtime.bucket,
            base_url=runtime.base_url,
            storage_prefix=runtime.storage_prefix,
            local_storage_dir=runtime.local_storage_dir,
            minio_endpoint=runtime.minio_endpoint,
            minio_secure=runtime.minio_secure,
            minio_access_key_set=bool(runtime.minio_access_key),
            minio_secret_key_set=bool(runtime.minio_secret_key),
            aliyun_oss_endpoint=runtime.aliyun_oss_endpoint,
            aliyun_oss_region=runtime.aliyun_oss_region,
            aliyun_oss_access_key_id_set=bool(runtime.aliyun_oss_access_key_id),
            aliyun_oss_access_key_secret_set=bool(runtime.aliyun_oss_access_key_secret),
        )

    def list_storage_channels(self) -> StorageChannelsResponse:
        channels = self._load_storage_channels_runtime()
        return StorageChannelsResponse(channels=channels)

    def update_storage_channels(
        self, payload: StorageChannelsUpdateRequest, user_id: int
    ) -> StorageChannelsResponse:
        channels = payload.channels
        if not channels:
            raise ValueError("至少需要一个存储渠道")
        if not any(item.enabled for item in channels):
            raise ValueError("至少需要启用一个存储渠道")

        normalized: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(channels):
            if item.id in seen_ids:
                raise ValueError("渠道 ID 重复")
            seen_ids.add(item.id)
            row = item.model_dump()
            row["priority"] = int(item.priority)
            row["order"] = index
            self._validate_provider_credentials(row)
            normalized.append(row)

        encrypted = encrypt_text(json.dumps(normalized, ensure_ascii=False))
        self.repo.upsert(STORAGE_CHANNELS_KEY, encrypted, is_secret=True)
        self.db.add(
            OperationLog(
                user_id=user_id,
                action="update_storage_channels",
                detail=f"count={len(normalized)}",
            )
        )
        self.db.commit()
        return self.list_storage_channels()

    def test_storage_channel(self, payload: StorageChannelTestRequest) -> None:
        merged = payload.model_dump()
        self._validate_provider_credentials(merged)
        key = f"test/{uuid4().hex}.txt"
        data = b"qrgift storage test"
        provider = merged["provider"]
        if provider == "aliyun":
            storage = AliyunOssStorage(config=merged)
        elif provider == "minio":
            storage = MinioStorage(config=merged)
        else:
            storage = LocalFileStorage(config=merged)
        storage.upload_bytes(key=key, data=data, content_type="text/plain")
        storage.delete(key)

    def get_claim_contact(self) -> ClaimContactResponse:
        item = self.repo.get_by_key(CLAIM_CONTACT_KEY)
        if not item or not item.config_value.strip():
            return ClaimContactResponse(contact_text=DEFAULT_CLAIM_CONTACT)
        return ClaimContactResponse(contact_text=item.config_value.strip())

    def update_claim_contact(self, contact_text: str, user_id: int) -> ClaimContactResponse:
        normalized = contact_text.strip()
        if not normalized:
            raise ValueError("联系方式不能为空")
        self.repo.upsert(CLAIM_CONTACT_KEY, normalized, is_secret=False)
        self.db.add(
            OperationLog(
                user_id=user_id,
                action="update_claim_contact",
                detail=f"contact={normalized[:80]}",
            )
        )
        self.db.commit()
        return ClaimContactResponse(contact_text=normalized)

    def update_storage_config(
        self, payload: StorageConfigUpdateRequest, user_id: int
    ) -> StorageConfigResponse:
        runtime = self._resolve_runtime_config()
        normalized = self._normalize_payload(payload.model_dump())
        merged = self._merge_runtime_with_payload(runtime, normalized)
        self._validate_provider_credentials(merged)

        for key, value in merged.items():
            if key in SECRET_KEYS:
                encrypted = encrypt_text(value) if value else ""
                self.repo.upsert(key, encrypted, is_secret=True)
                continue
            serialized = "true" if value is True else "false" if value is False else str(value)
            self.repo.upsert(key, serialized, is_secret=False)

        self.db.add(
            OperationLog(
                user_id=user_id,
                action="update_storage_config",
                detail=f"provider={merged['provider']}, bucket={merged['bucket']}",
            )
        )
        self.db.commit()
        return self.get_storage_config()

    def test_storage_config(self, payload: StorageConfigTestRequest) -> None:
        runtime = self._resolve_runtime_config()
        normalized = self._normalize_payload(payload.model_dump())
        merged = self._merge_runtime_with_payload(runtime, normalized)

        provider = merged["provider"]
        if provider == "aliyun":
            if normalized.get("aliyun_oss_access_key_id"):
                merged["aliyun_oss_access_key_id"] = normalized["aliyun_oss_access_key_id"]
            if normalized.get("aliyun_oss_access_key_secret"):
                merged["aliyun_oss_access_key_secret"] = normalized["aliyun_oss_access_key_secret"]
        elif provider == "minio":
            if normalized.get("minio_access_key"):
                merged["minio_access_key"] = normalized["minio_access_key"]
            if normalized.get("minio_secret_key"):
                merged["minio_secret_key"] = normalized["minio_secret_key"]

        self._validate_provider_credentials(merged)

        key = f"test/{uuid4().hex}.txt"
        data = b"qrgift storage test"
        if merged["provider"] == "aliyun":
            storage = AliyunOssStorage(config=merged)
        elif merged["provider"] == "minio":
            storage = MinioStorage(config=merged)
        else:
            storage = LocalFileStorage(config=merged)

        storage.upload_bytes(key=key, data=data, content_type="text/plain")
        storage.delete(key)

    def _resolve_runtime_config(self) -> StorageRuntimeConfig:
        channels = self._load_storage_channels_runtime()
        for channel in channels:
            if channel.enabled:
                return StorageRuntimeConfig(
                    provider=channel.provider,
                    bucket=channel.bucket,
                    base_url=channel.base_url,
                    storage_prefix=channel.storage_prefix,
                    local_storage_dir=channel.local_storage_dir,
                    minio_endpoint=channel.minio_endpoint,
                    minio_secure=channel.minio_secure,
                    minio_access_key=channel.minio_access_key,
                    minio_secret_key=channel.minio_secret_key,
                    aliyun_oss_endpoint=channel.aliyun_oss_endpoint,
                    aliyun_oss_region=channel.aliyun_oss_region,
                    aliyun_oss_access_key_id=channel.aliyun_oss_access_key_id,
                    aliyun_oss_access_key_secret=channel.aliyun_oss_access_key_secret,
                )

        defaults = self._default_runtime_dict()
        for item in self.repo.list_all():
            if item.config_key not in defaults:
                continue
            if item.is_secret:
                if not item.config_value:
                    defaults[item.config_key] = ""
                    continue
                try:
                    defaults[item.config_key] = decrypt_text(item.config_value)
                except Exception:
                    # 中文注释：兼容历史未加密或密钥变更导致的解密失败，避免服务整体不可用。
                    defaults[item.config_key] = ""
                continue
            defaults[item.config_key] = self._cast_plain(item.config_key, item.config_value)
        return StorageRuntimeConfig(**defaults)

    def _load_storage_channels_runtime(self) -> list[StorageChannelItem]:
        item = self.repo.get_by_key(STORAGE_CHANNELS_KEY)
        if item and item.config_value:
            try:
                decrypted = decrypt_text(item.config_value) if item.is_secret else item.config_value
                parsed = json.loads(decrypted)
                channels: list[StorageChannelItem] = []
                for row in parsed:
                    channels.append(StorageChannelItem(**row))
                channels.sort(key=lambda x: (x.priority, -len(x.name)), reverse=True)
                return channels
            except Exception:
                pass

        runtime = self._resolve_runtime_from_defaults_only()
        fallback = StorageChannelItem(
            id="default-local",
            name="默认本地",
            provider="local",
            enabled=True,
            priority=100,
            bucket=runtime.bucket,
            base_url=runtime.base_url,
            storage_prefix=runtime.storage_prefix,
            local_storage_dir=runtime.local_storage_dir,
            minio_endpoint=runtime.minio_endpoint,
            minio_secure=runtime.minio_secure,
            minio_access_key=runtime.minio_access_key,
            minio_secret_key=runtime.minio_secret_key,
            aliyun_oss_endpoint=runtime.aliyun_oss_endpoint,
            aliyun_oss_region=runtime.aliyun_oss_region,
            aliyun_oss_access_key_id=runtime.aliyun_oss_access_key_id,
            aliyun_oss_access_key_secret=runtime.aliyun_oss_access_key_secret,
            minio_access_key_set=bool(runtime.minio_access_key),
            minio_secret_key_set=bool(runtime.minio_secret_key),
            aliyun_oss_access_key_id_set=bool(runtime.aliyun_oss_access_key_id),
            aliyun_oss_access_key_secret_set=bool(runtime.aliyun_oss_access_key_secret),
        )
        return [fallback]

    def _resolve_runtime_from_defaults_only(self) -> StorageRuntimeConfig:
        defaults = self._default_runtime_dict()
        for item in self.repo.list_all():
            if item.config_key not in defaults:
                continue
            if item.is_secret:
                if not item.config_value:
                    defaults[item.config_key] = ""
                    continue
                try:
                    defaults[item.config_key] = decrypt_text(item.config_value)
                except Exception:
                    defaults[item.config_key] = ""
                continue
            defaults[item.config_key] = self._cast_plain(item.config_key, item.config_value)
        return StorageRuntimeConfig(**defaults)

    @staticmethod
    def _cast_plain(key: str, value: str) -> Any:
        if key == "minio_secure":
            return value.lower() == "true"
        return value

    @staticmethod
    def _merge_runtime_with_payload(
        runtime: StorageRuntimeConfig, payload: dict[str, Any]
    ) -> dict[str, Any]:
        current = runtime.__dict__.copy()
        for key, value in payload.items():
            if key in SECRET_KEYS and not str(value).strip():
                continue
            current[key] = value
        return current

    @staticmethod
    def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        normalized = payload.copy()
        for key in STRIP_KEYS:
            value = normalized.get(key)
            if isinstance(value, str):
                normalized[key] = value.strip()

        for endpoint_key in ("minio_endpoint", "aliyun_oss_endpoint"):
            raw = normalized.get(endpoint_key)
            if not isinstance(raw, str) or not raw:
                continue
            endpoint = raw.replace("https://", "").replace("http://", "").strip().strip("/")
            endpoint = endpoint.split("/")[0]
            bucket = normalized.get("bucket", "")
            if isinstance(bucket, str) and bucket and endpoint.startswith(f"{bucket}."):
                # 中文注释：用户可能填写了 bucket.endpoint，这里自动归一化成 endpoint。
                endpoint = endpoint[len(bucket) + 1 :]
            normalized[endpoint_key] = endpoint
        return normalized

    @staticmethod
    def _validate_provider_credentials(merged: dict[str, Any]) -> None:
        provider = merged["provider"]
        if provider == "minio":
            if not merged["minio_access_key"] or not merged["minio_secret_key"]:
                raise ValueError("MinIO Access Key 和 Secret Key 不能为空")
            return
        if provider == "local":
            if not str(merged.get("local_storage_dir", "")).strip():
                raise ValueError("本地存储目录不能为空")
            return
        if not merged["aliyun_oss_access_key_id"] or not merged["aliyun_oss_access_key_secret"]:
            raise ValueError("阿里云 AccessKey ID 和 Secret 不能为空")

    @staticmethod
    def _default_runtime_dict() -> dict[str, Any]:
        settings = get_settings()
        return {
            "provider": settings.storage_provider,
            "bucket": settings.storage_bucket,
            "base_url": settings.storage_base_url,
            "storage_prefix": settings.storage_prefix,
            "local_storage_dir": settings.local_storage_dir,
            "minio_endpoint": settings.minio_endpoint,
            "minio_secure": settings.minio_secure,
            "minio_access_key": settings.minio_access_key,
            "minio_secret_key": settings.minio_secret_key,
            "aliyun_oss_endpoint": settings.aliyun_oss_endpoint,
            "aliyun_oss_region": settings.aliyun_oss_region,
            "aliyun_oss_access_key_id": settings.aliyun_oss_access_key_id,
            "aliyun_oss_access_key_secret": settings.aliyun_oss_access_key_secret,
        }


def get_runtime_storage_config(db: Session) -> StorageRuntimeConfig:
    return SystemConfigService(db)._resolve_runtime_config()


def get_runtime_storage_channels(db: Session) -> list[StorageChannelItem]:
    channels = SystemConfigService(db).list_storage_channels().channels
    return [item for item in channels if item.enabled]


def get_claim_contact_text(db: Session) -> str:
    return SystemConfigService(db).get_claim_contact().contact_text
