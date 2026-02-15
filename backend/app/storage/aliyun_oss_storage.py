from io import BytesIO

import oss2

from app.core.config import get_settings


class AliyunOssStorage:
    def __init__(self, config: dict | None = None) -> None:
        settings = get_settings()
        resolved = config or {}
        self.endpoint = resolved.get("aliyun_oss_endpoint") or settings.aliyun_oss_endpoint
        access_key_id = (
            resolved.get("aliyun_oss_access_key_id") or settings.aliyun_oss_access_key_id
        )
        access_key_secret = (
            resolved.get("aliyun_oss_access_key_secret") or settings.aliyun_oss_access_key_secret
        )
        auth = oss2.Auth(access_key_id, access_key_secret)
        endpoint = f"https://{self.endpoint}"
        self.bucket_name = str(resolved.get("bucket") or settings.storage_bucket)
        self.base_url: str = str(resolved.get("base_url") or settings.storage_base_url)
        self.bucket = oss2.Bucket(auth, endpoint, self.bucket_name)
        try:
            self.bucket.get_bucket_info()
        except Exception as exc:
            raise RuntimeError(
                f"阿里云 OSS 连接失败，请检查 endpoint、Bucket 和密钥: {exc}"
            ) from exc

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        headers = {"Content-Type": content_type}
        try:
            self.bucket.put_object(key, BytesIO(data), headers=headers)
        except Exception as exc:
            raise RuntimeError(f"阿里云 OSS 上传失败: {exc}") from exc
        if self.base_url:
            return f"{self.base_url.rstrip('/')}/{key}"
        return f"https://{self.bucket_name}.{self.endpoint}/{key}"

    def delete(self, key: str) -> None:
        try:
            self.bucket.delete_object(key)
        except Exception as exc:
            raise RuntimeError(f"阿里云 OSS 删除对象失败: {exc}") from exc

    def download_bytes(self, key: str) -> bytes:
        obj = self.bucket.get_object(key)
        content = obj.read()
        if isinstance(content, bytes):
            return content
        return str(content).encode("utf-8")

    def generate_presigned_url(self, key: str, expires: int = 3600) -> str:
        return self.bucket.sign_url("GET", key, expires)
