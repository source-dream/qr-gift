from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.system_config_service import (
    get_runtime_storage_channels,
    get_runtime_storage_config,
)
from app.schemas.system_config import StorageChannelItem
from app.storage.aliyun_oss_storage import AliyunOssStorage
from app.storage.base import ObjectStorage
from app.storage.local_storage import LocalFileStorage
from app.storage.minio_storage import MinioStorage


def get_storage(db: Session | None = None) -> ObjectStorage:
    settings = get_settings()
    if db is None:
        provider = settings.storage_provider.strip().lower()
        if provider == "local":
            return LocalFileStorage()
        if provider == "aliyun":
            return AliyunOssStorage()
        return MinioStorage()

    runtime = get_runtime_storage_config(db)
    runtime_dict = runtime.__dict__
    return create_storage_from_config(runtime_dict)


def create_storage_from_channel(channel: StorageChannelItem) -> ObjectStorage:
    payload = channel.model_dump()
    return create_storage_from_config(payload)


def create_storage_from_config(config: dict) -> ObjectStorage:
    provider = str(config.get("provider", "local")).strip().lower()
    if provider == "local":
        return LocalFileStorage(config=config)
    if provider == "aliyun":
        return AliyunOssStorage(config=config)
    return MinioStorage(config=config)


def get_enabled_storage_channels(db: Session) -> list[StorageChannelItem]:
    channels = get_runtime_storage_channels(db)
    return sorted(channels, key=lambda item: item.priority, reverse=True)
