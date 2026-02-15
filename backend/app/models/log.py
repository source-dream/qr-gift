from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ClaimLog(Base, TimestampMixin):
    __tablename__ = "claim_logs"
    __table_args__ = (Index("ix_claim_logs_qrcode_created", "qrcode_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    qrcode_id: Mapped[int] = mapped_column(ForeignKey("qrcodes.id", ondelete="CASCADE"), index=True)
    ip: Mapped[str] = mapped_column(String(64), default="")
    ua: Mapped[str] = mapped_column(String(255), default="")
    result: Mapped[str] = mapped_column(String(30), index=True)
    reason: Mapped[str] = mapped_column(String(255), default="")


class OperationLog(Base, TimestampMixin):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    detail: Mapped[str] = mapped_column(Text, default="")


class SecurityRule(Base, TimestampMixin):
    __tablename__ = "security_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_key: Mapped[str] = mapped_column(String(80), unique=True)
    rule_value: Mapped[str] = mapped_column(Text, default="")


class AccessLog(Base, TimestampMixin):
    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(20), index=True, default="admin")
    path: Mapped[str] = mapped_column(String(255), index=True)
    method: Mapped[str] = mapped_column(String(10), default="GET")
    ip: Mapped[str] = mapped_column(String(64), default="")
    ua: Mapped[str] = mapped_column(String(255), default="")
    status_code: Mapped[int] = mapped_column(index=True)
    latency_ms: Mapped[int] = mapped_column(default=0)
