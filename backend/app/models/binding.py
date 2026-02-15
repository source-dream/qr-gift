from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Binding(Base, TimestampMixin):
    __tablename__ = "bindings"
    __table_args__ = (
        UniqueConstraint("qrcode_id", name="uq_bindings_qrcode_id"),
        UniqueConstraint("red_packet_id", name="uq_bindings_red_packet_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    qrcode_id: Mapped[int] = mapped_column(ForeignKey("qrcodes.id", ondelete="CASCADE"), index=True)
    red_packet_id: Mapped[int] = mapped_column(
        ForeignKey("red_packets.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
