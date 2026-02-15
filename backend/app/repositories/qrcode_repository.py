from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.qrcode import Qrcode, QrcodeBatch


class QrcodeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_batch(self, batch_no: str, amount: int) -> QrcodeBatch:
        batch = QrcodeBatch(batch_no=batch_no, amount=amount)
        self.db.add(batch)
        self.db.flush()
        return batch

    def create_qrcode(self, batch_id: int, short_code: str, image_url: str, object_key: str) -> Qrcode:
        item = Qrcode(
            batch_id=batch_id,
            short_code=short_code,
            status="created",
            image_url=image_url,
            object_key=object_key,
        )
        self.db.add(item)
        return item

    def list_qrcodes(self, limit: int = 50) -> list[Qrcode]:
        stmt = select(Qrcode).order_by(Qrcode.id.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_by_short_code(self, short_code: str) -> Qrcode | None:
        stmt = select(Qrcode).where(Qrcode.short_code == short_code)
        return self.db.scalar(stmt)
