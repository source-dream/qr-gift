"""add gift qrcode and access logs

Revision ID: 0003_gift_and_access_logs
Revises: 0002_add_system_configs
Create Date: 2026-02-15 22:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_gift_and_access_logs"
down_revision: str | None = "0002_add_system_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gift_qrcodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("activate_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expire_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("binding_mode", sa.String(length=20), nullable=False),
        sa.Column("style_type", sa.String(length=30), nullable=False),
        sa.Column("style_config", sa.Text(), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gift_qrcodes"),
        sa.UniqueConstraint("token_hash", name="uq_gift_qrcodes_token_hash"),
    )
    op.create_index("ix_gift_qrcodes_status", "gift_qrcodes", ["status"], unique=False)
    op.create_index("ix_gift_qrcodes_token_hash", "gift_qrcodes", ["token_hash"], unique=False)

    op.create_table(
        "gift_bindings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gift_qrcode_id", sa.Integer(), nullable=False),
        sa.Column("red_packet_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["gift_qrcode_id"],
            ["gift_qrcodes.id"],
            name="fk_gift_bindings_gift_qrcode_id_gift_qrcodes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["red_packet_id"],
            ["red_packets.id"],
            name="fk_gift_bindings_red_packet_id_red_packets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gift_bindings"),
        sa.UniqueConstraint("gift_qrcode_id", name="uq_gift_bindings_gift_qrcode_id"),
        sa.UniqueConstraint("red_packet_id", name="uq_gift_bindings_red_packet_id"),
    )
    op.create_index(
        "ix_gift_bindings_gift_qrcode_id", "gift_bindings", ["gift_qrcode_id"], unique=False
    )
    op.create_index(
        "ix_gift_bindings_red_packet_id", "gift_bindings", ["red_packet_id"], unique=False
    )
    op.create_index("ix_gift_bindings_status", "gift_bindings", ["status"], unique=False)

    op.create_table(
        "gift_claim_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gift_qrcode_id", sa.Integer(), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("ua", sa.String(length=255), nullable=False),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["gift_qrcode_id"],
            ["gift_qrcodes.id"],
            name="fk_gift_claim_logs_gift_qrcode_id_gift_qrcodes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gift_claim_logs"),
    )
    op.create_index(
        "ix_gift_claim_logs_gift_qrcode_id", "gift_claim_logs", ["gift_qrcode_id"], unique=False
    )
    op.create_index("ix_gift_claim_logs_result", "gift_claim_logs", ["result"], unique=False)

    op.create_table(
        "access_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("ua", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_access_logs_user_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_access_logs"),
    )
    op.create_index("ix_access_logs_path", "access_logs", ["path"], unique=False)
    op.create_index("ix_access_logs_source", "access_logs", ["source"], unique=False)
    op.create_index("ix_access_logs_status_code", "access_logs", ["status_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_access_logs_status_code", table_name="access_logs")
    op.drop_index("ix_access_logs_source", table_name="access_logs")
    op.drop_index("ix_access_logs_path", table_name="access_logs")
    op.drop_table("access_logs")
    op.drop_index("ix_gift_claim_logs_result", table_name="gift_claim_logs")
    op.drop_index("ix_gift_claim_logs_gift_qrcode_id", table_name="gift_claim_logs")
    op.drop_table("gift_claim_logs")
    op.drop_index("ix_gift_bindings_status", table_name="gift_bindings")
    op.drop_index("ix_gift_bindings_red_packet_id", table_name="gift_bindings")
    op.drop_index("ix_gift_bindings_gift_qrcode_id", table_name="gift_bindings")
    op.drop_table("gift_bindings")
    op.drop_index("ix_gift_qrcodes_token_hash", table_name="gift_qrcodes")
    op.drop_index("ix_gift_qrcodes_status", table_name="gift_qrcodes")
    op.drop_table("gift_qrcodes")
