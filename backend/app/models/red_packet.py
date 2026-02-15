from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RedPacketBatch(Base, TimestampMixin):
    __tablename__ = "red_packet_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(30), default="manual")


class RedPacket(Base, TimestampMixin):
    __tablename__ = "red_packets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("red_packet_batches.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120), default="")
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    level: Mapped[int] = mapped_column(Integer, default=1)
    content_type: Mapped[str] = mapped_column(String(20), default="url")
    content_value: Mapped[str] = mapped_column(Text, default="")
    content_image_url: Mapped[str] = mapped_column(String(500), default="")
    content_image_key: Mapped[str] = mapped_column(String(255), default="")
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    claim_url: Mapped[str] = mapped_column(String(800))
    status: Mapped[str] = mapped_column(String(20), default="idle", index=True)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RedPacketCategory(Base, TimestampMixin):
    __tablename__ = "red_packet_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_content_types: Mapped[str] = mapped_column(String(60), default="url")


class RedPacketTag(Base, TimestampMixin):
    __tablename__ = "red_packet_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)


class RedPacketTagBinding(Base, TimestampMixin):
    __tablename__ = "red_packet_tag_bindings"
    __table_args__ = (UniqueConstraint("red_packet_id", "tag_id", name="uq_red_packet_tag_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    red_packet_id: Mapped[int] = mapped_column(
        ForeignKey("red_packets.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("red_packet_tags.id", ondelete="CASCADE"), index=True
    )
