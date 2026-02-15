from io import BytesIO
from datetime import timedelta

from minio import Minio

from app.core.config import get_settings


class MinioStorage:
    def __init__(self, config: dict | None = None) -> None:
        settings = get_settings()
        resolved = config or {}
        self.bucket = resolved.get("bucket") or settings.storage_bucket
        self.client = Minio(
            endpoint=resolved.get("minio_endpoint") or settings.minio_endpoint,
            access_key=resolved.get("minio_access_key") or settings.minio_access_key,
            secret_key=resolved.get("minio_secret_key") or settings.minio_secret_key,
            secure=bool(resolved.get("minio_secure", settings.minio_secure)),
        )
        self.base_url = str(resolved.get("base_url") or settings.storage_base_url)
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as exc:
            raise RuntimeError(f"MinIO 连接失败，请检查 endpoint、账号和服务状态: {exc}") from exc

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        stream = BytesIO(data)
        try:
            self.client.put_object(
                self.bucket,
                key,
                stream,
                length=len(data),
                content_type=content_type,
            )
        except Exception as exc:
            raise RuntimeError(f"MinIO 上传失败: {exc}") from exc
        if self.base_url:
            return f"{self.base_url.rstrip('/')}/{key}"
        return self.generate_presigned_url(key, expires=60 * 60 * 24)

    def delete(self, key: str) -> None:
        try:
            self.client.remove_object(self.bucket, key)
        except Exception as exc:
            raise RuntimeError(f"MinIO 删除对象失败: {exc}") from exc

    def download_bytes(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def generate_presigned_url(self, key: str, expires: int = 3600) -> str:
        return self.client.presigned_get_object(
            self.bucket, key, expires=timedelta(seconds=expires)
        )
