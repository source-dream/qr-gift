"""add dispatch strategy, multi-binding and red packet level

Revision ID: 0004_multi_binding_and_level
Revises: 0003_gift_and_access_logs
Create Date: 2026-02-15 23:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0004_multi_binding_and_level"
down_revision: str | None = "0003_gift_and_access_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def has_col(table: str, col: str) -> bool:
        return any(c["name"] == col for c in inspector.get_columns(table))

    if not has_col("red_packets", "level"):
        op.add_column(
            "red_packets", sa.Column("level", sa.Integer(), server_default="1", nullable=False)
        )

    if not has_col("gift_qrcodes", "dispatch_strategy"):
        op.add_column(
            "gift_qrcodes",
            sa.Column(
                "dispatch_strategy", sa.String(length=20), server_default="random", nullable=False
            ),
        )

    if not has_col("gift_claim_logs", "red_packet_id"):
        op.add_column("gift_claim_logs", sa.Column("red_packet_id", sa.Integer(), nullable=True))
    if not has_col("gift_claim_logs", "dispatch_strategy"):
        op.add_column(
            "gift_claim_logs",
            sa.Column("dispatch_strategy", sa.String(length=20), server_default="", nullable=False),
        )

    index_names = {idx["name"] for idx in inspector.get_indexes("gift_claim_logs")}
    if "ix_gift_claim_logs_red_packet_id" not in index_names:
        op.create_index(
            "ix_gift_claim_logs_red_packet_id", "gift_claim_logs", ["red_packet_id"], unique=False
        )

    # 中文注释：SQLite 不支持直接删除唯一约束，这里通过重建表实现 gift 多红包绑定。
    create_sql = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type='table' AND name='gift_bindings'")
    ).scalar_one_or_none()
    need_rebuild = bool(create_sql and "UNIQUE (gift_qrcode_id)" in create_sql)
    has_old_table = bool(
        bind.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='gift_bindings_old'")
        ).scalar_one_or_none()
    )

    if need_rebuild:
        op.rename_table("gift_bindings", "gift_bindings_old")
        op.create_table(
            "gift_bindings",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("gift_qrcode_id", sa.Integer(), nullable=False),
            sa.Column("red_packet_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
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
            sa.UniqueConstraint("red_packet_id", name="uq_gift_bindings_red_packet_id"),
            sa.UniqueConstraint("gift_qrcode_id", "red_packet_id", name="uq_gift_bindings_pair"),
        )
        op.execute(
            """
            INSERT INTO gift_bindings (id, gift_qrcode_id, red_packet_id, status, created_at, updated_at)
            SELECT id, gift_qrcode_id, red_packet_id, status, created_at, updated_at
            FROM gift_bindings_old
            """
        )
        op.drop_table("gift_bindings_old")
        op.create_index(
            "ix_gift_bindings_gift_qrcode_id", "gift_bindings", ["gift_qrcode_id"], unique=False
        )
        op.create_index(
            "ix_gift_bindings_red_packet_id", "gift_bindings", ["red_packet_id"], unique=False
        )
        op.create_index("ix_gift_bindings_status", "gift_bindings", ["status"], unique=False)

    if has_old_table:
        op.execute(
            """
            INSERT OR IGNORE INTO gift_bindings (id, gift_qrcode_id, red_packet_id, status, created_at, updated_at)
            SELECT id, gift_qrcode_id, red_packet_id, status, created_at, updated_at
            FROM gift_bindings_old
            """
        )
        op.drop_table("gift_bindings_old")

    index_names = {idx["name"] for idx in inspect(bind).get_indexes("gift_bindings")}
    if "ix_gift_bindings_gift_qrcode_id" not in index_names:
        op.create_index(
            "ix_gift_bindings_gift_qrcode_id", "gift_bindings", ["gift_qrcode_id"], unique=False
        )
    if "ix_gift_bindings_red_packet_id" not in index_names:
        op.create_index(
            "ix_gift_bindings_red_packet_id", "gift_bindings", ["red_packet_id"], unique=False
        )
    if "ix_gift_bindings_status" not in index_names:
        op.create_index("ix_gift_bindings_status", "gift_bindings", ["status"], unique=False)


def downgrade() -> None:
    op.rename_table("gift_bindings", "gift_bindings_new")
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
    op.execute(
        """
        INSERT INTO gift_bindings (id, gift_qrcode_id, red_packet_id, status, created_at, updated_at)
        SELECT id, gift_qrcode_id, red_packet_id, status, created_at, updated_at
        FROM gift_bindings_new
        """
    )
    op.drop_table("gift_bindings_new")

    op.drop_index("ix_gift_claim_logs_red_packet_id", table_name="gift_claim_logs")
    op.drop_column("gift_claim_logs", "dispatch_strategy")
    op.drop_column("gift_claim_logs", "red_packet_id")
    op.drop_column("gift_qrcodes", "dispatch_strategy")
    op.drop_column("red_packets", "level")
