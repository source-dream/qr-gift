from datetime import datetime
from io import BytesIO
from secrets import token_urlsafe

import qrcode
from sqlalchemy.orm import Session

from app.repositories.qrcode_repository import QrcodeRepository
from app.services.system_config_service import get_runtime_storage_config
from app.storage.factory import get_storage


class QrcodeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QrcodeRepository(db)
        self.storage = get_storage(db)
        self.runtime_storage = get_runtime_storage_config(db)

    def create_batch(self, amount: int) -> str:
        # 中文注释：批次号用于追踪本次生成任务，便于导出、审计和问题回溯。
        batch_no = f"QR{datetime.now().strftime('%Y%m%d%H%M%S')}"
        batch = self.repo.create_batch(batch_no=batch_no, amount=amount)
        for _ in range(amount):
            # 中文注释：短码作为公开扫码入口，不直接暴露数据库主键。
            short_code = token_urlsafe(8).replace("-", "").replace("_", "")[:12]
            url = f"/r/{short_code}"
            image_data = self._render_qrcode(url)
            object_key = self._build_object_key(batch_no, short_code)
            image_url = self.storage.upload_bytes(
                key=object_key,
                data=image_data,
                content_type="image/png",
            )
            self.repo.create_qrcode(batch.id, short_code, image_url, object_key)

        self.db.commit()
        return batch_no

    def _render_qrcode(self, content: str) -> bytes:
        qr = qrcode.QRCode(border=2, box_size=10)
        qr.add_data(content)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        image.save(buffer, "PNG")
        return buffer.getvalue()

    def _build_object_key(self, batch_no: str, short_code: str) -> str:
        now = datetime.now()
        # 中文注释：对象路径按年月与批次组织，便于后续清理与审计追踪。
        relative = f"qrcodes/{now:%Y}/{now:%m}/{batch_no}/{short_code}.png"
        prefix = self.runtime_storage.storage_prefix.strip().strip("/")
        if not prefix:
            return relative
        return f"{prefix}/{relative}"
