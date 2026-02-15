from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="QRGift API", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    secret_key: str = Field(default="please-change-me", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=120, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    frontend_base_url: str = Field(default="http://127.0.0.1:5173", alias="FRONTEND_BASE_URL")

    sqlite_path: str = Field(default="./data/qrgift.db", alias="SQLITE_PATH")

    storage_provider: str = Field(default="local", alias="STORAGE_PROVIDER")
    storage_bucket: str = Field(default="qrgift", alias="STORAGE_BUCKET")
    storage_base_url: str = Field(default="", alias="STORAGE_BASE_URL")
    storage_prefix: str = Field(default="", alias="STORAGE_PREFIX")
    local_storage_dir: str = Field(default="./data/object-storage", alias="LOCAL_STORAGE_DIR")

    minio_endpoint: str = Field(default="127.0.0.1:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    aliyun_oss_endpoint: str = Field(
        default="oss-cn-hangzhou.aliyuncs.com", alias="ALIYUN_OSS_ENDPOINT"
    )
    aliyun_oss_region: str = Field(default="cn-hangzhou", alias="ALIYUN_OSS_REGION")
    aliyun_oss_access_key_id: str = Field(default="", alias="ALIYUN_OSS_ACCESS_KEY_ID")
    aliyun_oss_access_key_secret: str = Field(default="", alias="ALIYUN_OSS_ACCESS_KEY_SECRET")

    @property
    def sqlite_url(self) -> str:
        db_path = Path(self.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.resolve()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
