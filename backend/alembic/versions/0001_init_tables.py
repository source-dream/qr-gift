"""initial tables

Revision ID: 0001_init_tables
Revises:
Create Date: 2026-02-15 20:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_init_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qrcode_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_no", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_qrcode_batches"),
    )
    op.create_index("ix_qrcode_batches_batch_no", "qrcode_batches", ["batch_no"], unique=True)

    op.create_table(
        "red_packet_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_no", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_red_packet_batches"),
    )
    op.create_index("ix_red_packet_batches_batch_no", "red_packet_batches", ["batch_no"], unique=True)

    op.create_table(
        "security_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_key", sa.String(length=80), nullable=False),
        sa.Column("rule_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_security_rules"),
        sa.UniqueConstraint("rule_key", name="uq_security_rules_rule_key"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "qrcodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("short_code", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["batch_id"], ["qrcode_batches.id"], name="fk_qrcodes_batch_id_qrcode_batches", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_qrcodes"),
        sa.UniqueConstraint("short_code", name="uq_qrcodes_short_code"),
    )
    op.create_index("ix_qrcodes_short_code", "qrcodes", ["short_code"], unique=False)

    op.create_table(
        "red_packets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("claim_url", sa.String(length=800), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["batch_id"], ["red_packet_batches.id"], name="fk_red_packets_batch_id_red_packet_batches", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_red_packets"),
    )
    op.create_index("ix_red_packets_status", "red_packets", ["status"], unique=False)

    op.create_table(
        "bindings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("qrcode_id", sa.Integer(), nullable=False),
        sa.Column("red_packet_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["qrcode_id"], ["qrcodes.id"], name="fk_bindings_qrcode_id_qrcodes", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["red_packet_id"], ["red_packets.id"], name="fk_bindings_red_packet_id_red_packets", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_bindings"),
        sa.UniqueConstraint("qrcode_id", name="uq_bindings_qrcode_id"),
        sa.UniqueConstraint("red_packet_id", name="uq_bindings_red_packet_id"),
    )
    op.create_index("ix_bindings_qrcode_id", "bindings", ["qrcode_id"], unique=False)
    op.create_index("ix_bindings_red_packet_id", "bindings", ["red_packet_id"], unique=False)
    op.create_index("ix_bindings_status", "bindings", ["status"], unique=False)

    op.create_table(
        "claim_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("qrcode_id", sa.Integer(), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("ua", sa.String(length=255), nullable=False),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["qrcode_id"], ["qrcodes.id"], name="fk_claim_logs_qrcode_id_qrcodes", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_claim_logs"),
    )
    op.create_index("ix_claim_logs_qrcode_id", "claim_logs", ["qrcode_id"], unique=False)
    op.create_index("ix_claim_logs_result", "claim_logs", ["result"], unique=False)
    op.create_index("ix_claim_logs_qrcode_created", "claim_logs", ["qrcode_id", "created_at"], unique=False)

    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_operation_logs_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_operation_logs"),
    )
    op.create_index("ix_operation_logs_action", "operation_logs", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_operation_logs_action", table_name="operation_logs")
    op.drop_table("operation_logs")
    op.drop_index("ix_claim_logs_qrcode_created", table_name="claim_logs")
    op.drop_index("ix_claim_logs_result", table_name="claim_logs")
    op.drop_index("ix_claim_logs_qrcode_id", table_name="claim_logs")
    op.drop_table("claim_logs")
    op.drop_index("ix_bindings_status", table_name="bindings")
    op.drop_index("ix_bindings_red_packet_id", table_name="bindings")
    op.drop_index("ix_bindings_qrcode_id", table_name="bindings")
    op.drop_table("bindings")
    op.drop_index("ix_red_packets_status", table_name="red_packets")
    op.drop_table("red_packets")
    op.drop_index("ix_qrcodes_short_code", table_name="qrcodes")
    op.drop_table("qrcodes")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.drop_table("security_rules")
    op.drop_index("ix_red_packet_batches_batch_no", table_name="red_packet_batches")
    op.drop_table("red_packet_batches")
    op.drop_index("ix_qrcode_batches_batch_no", table_name="qrcode_batches")
    op.drop_table("qrcode_batches")
