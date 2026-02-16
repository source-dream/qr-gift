from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GiftQrcode(Base, TimestampMixin):
    __tablename__ = "gift_qrcodes"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_gift_qrcodes_token_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), index=True, default="draft")
    token_plain: Mapped[str] = mapped_column(String(128), default="", index=True)
    token_hash: Mapped[str] = mapped_column(String(128), index=True)
    activate_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    binding_mode: Mapped[str] = mapped_column(String(20), default="manual")
    dispatch_strategy: Mapped[str] = mapped_column(String(20), default="random")
    style_type: Mapped[str] = mapped_column(String(30), default="festival")
    style_config: Mapped[str] = mapped_column(Text, default="{}")
    storage_channel_id: Mapped[str] = mapped_column(String(64), default="")
    object_key: Mapped[str] = mapped_column(String(255), default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")


class GiftBinding(Base, TimestampMixin):
    __tablename__ = "gift_bindings"
    __table_args__ = (
        UniqueConstraint("red_packet_id", name="uq_gift_bindings_red_packet_id"),
        UniqueConstraint("gift_qrcode_id", "red_packet_id", name="uq_gift_bindings_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gift_qrcode_id: Mapped[int] = mapped_column(
        ForeignKey("gift_qrcodes.id", ondelete="CASCADE"), index=True
    )
    red_packet_id: Mapped[int] = mapped_column(
        ForeignKey("red_packets.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)


class GiftClaimLog(Base, TimestampMixin):
    __tablename__ = "gift_claim_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gift_qrcode_id: Mapped[int] = mapped_column(
        ForeignKey("gift_qrcodes.id", ondelete="CASCADE"), index=True
    )
    red_packet_id: Mapped[int | None] = mapped_column(
        ForeignKey("red_packets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dispatch_strategy: Mapped[str] = mapped_column(String(20), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    ua: Mapped[str] = mapped_column(String(255), default="")
    result: Mapped[str] = mapped_column(String(30), index=True)
    reason: Mapped[str] = mapped_column(String(255), default="")
