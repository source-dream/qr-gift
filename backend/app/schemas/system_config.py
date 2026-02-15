from pydantic import BaseModel, Field, model_validator


class StorageConfigResponse(BaseModel):
    provider: str
    bucket: str
    base_url: str
    storage_prefix: str
    local_storage_dir: str
    minio_endpoint: str
    minio_secure: bool
    minio_access_key_set: bool
    minio_secret_key_set: bool
    aliyun_oss_endpoint: str
    aliyun_oss_region: str
    aliyun_oss_access_key_id_set: bool
    aliyun_oss_access_key_secret_set: bool


class StorageConfigUpdateRequest(BaseModel):
    provider: str = Field(pattern="^(local|minio|aliyun)$")
    bucket: str = Field(min_length=1, max_length=120)
    base_url: str = ""
    storage_prefix: str = ""
    local_storage_dir: str = ""

    minio_endpoint: str = ""
    minio_secure: bool = False
    minio_access_key: str = ""
    minio_secret_key: str = ""

    aliyun_oss_endpoint: str = ""
    aliyun_oss_region: str = ""
    aliyun_oss_access_key_id: str = ""
    aliyun_oss_access_key_secret: str = ""

    @model_validator(mode="after")
    def validate_by_provider(self):
        if self.provider == "minio":
            if not self.minio_endpoint.strip():
                raise ValueError("MinIO endpoint 不能为空")
        if self.provider == "local":
            if not self.local_storage_dir.strip():
                raise ValueError("本地存储目录不能为空")
        if self.provider == "aliyun":
            if not self.aliyun_oss_endpoint.strip():
                raise ValueError("阿里云 OSS endpoint 不能为空")
        return self


class StorageConfigTestRequest(BaseModel):
    provider: str = Field(pattern="^(local|minio|aliyun)$")
    bucket: str = Field(min_length=1, max_length=120)
    base_url: str = ""
    storage_prefix: str = ""
    local_storage_dir: str = ""

    minio_endpoint: str = ""
    minio_secure: bool = False
    minio_access_key: str = ""
    minio_secret_key: str = ""

    aliyun_oss_endpoint: str = ""
    aliyun_oss_region: str = ""
    aliyun_oss_access_key_id: str = ""
    aliyun_oss_access_key_secret: str = ""


class ClaimContactResponse(BaseModel):
    contact_text: str


class ClaimContactUpdateRequest(BaseModel):
    contact_text: str = Field(min_length=1, max_length=200)
