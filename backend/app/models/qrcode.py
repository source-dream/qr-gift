from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class QrcodeBatch(Base, TimestampMixin):
    __tablename__ = "qrcode_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    amount: Mapped[int] = mapped_column(Integer, default=0)

    qrcodes = relationship("Qrcode", back_populates="batch")


class Qrcode(Base, TimestampMixin):
    __tablename__ = "qrcodes"
    __table_args__ = (UniqueConstraint("short_code", name="uq_qrcodes_short_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("qrcode_batches.id", ondelete="CASCADE"))
    short_code: Mapped[str] = mapped_column(String(24), index=True)
    status: Mapped[str] = mapped_column(String(20), default="created")
    object_key: Mapped[str] = mapped_column(String(255), default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")

    batch = relationship("QrcodeBatch", back_populates="qrcodes")
