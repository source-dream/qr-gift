from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.system_config_service import get_runtime_storage_config
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
    provider = runtime.provider.strip().lower()
    if provider == "local":
        return LocalFileStorage(config=runtime_dict)
    try:
        if provider == "aliyun":
            return AliyunOssStorage(config=runtime_dict)
        return MinioStorage(config=runtime_dict)
    except Exception:
        # 中文注释：当远程存储配置不可用时自动回退本地存储，确保核心流程可继续使用。
        return LocalFileStorage(config=runtime_dict)
