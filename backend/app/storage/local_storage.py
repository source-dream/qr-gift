from pathlib import Path

from app.core.config import get_settings


class LocalFileStorage:
    def __init__(self, config: dict | None = None) -> None:
        settings = get_settings()
        resolved = config or {}
        root = resolved.get("local_storage_dir") or settings.local_storage_dir
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        target = self._resolve_target(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target.as_uri()

    def delete(self, key: str) -> None:
        target = self._resolve_target(key)
        if target.exists():
            target.unlink()

    def download_bytes(self, key: str) -> bytes:
        target = self._resolve_target(key)
        if not target.exists():
            raise FileNotFoundError(f"本地对象不存在: {key}")
        return target.read_bytes()

    def generate_presigned_url(self, key: str, expires: int = 3600) -> str:
        # 中文注释：本地存储不提供外部签名地址，调用方应改用应用内部下载接口。
        return f"local://{key}"

    def _resolve_target(self, key: str) -> Path:
        safe = key.strip().lstrip("/")
        if not safe:
            raise ValueError("对象 key 不能为空")
        path = (self.root / safe).resolve()
        if self.root not in path.parents and path != self.root:
            raise ValueError("对象 key 非法")
        return path
