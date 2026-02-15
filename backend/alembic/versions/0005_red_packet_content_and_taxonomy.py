"""red packet content and taxonomy

Revision ID: 0005_red_packet_content_and_taxonomy
Revises: 0004_multi_binding_and_level
Create Date: 2026-02-16 00:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0005_red_packet_content_and_taxonomy"
down_revision: str | None = "0004_multi_binding_and_level"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def has_table(name: str) -> bool:
        return name in inspector.get_table_names()

    def has_col(table: str, col: str) -> bool:
        return any(c["name"] == col for c in inspector.get_columns(table))

    if not has_col("red_packets", "title"):
        op.add_column(
            "red_packets",
            sa.Column("title", sa.String(length=120), server_default="", nullable=False),
        )
    if not has_col("red_packets", "category_id"):
        op.add_column("red_packets", sa.Column("category_id", sa.Integer(), nullable=True))
    if not has_col("red_packets", "content_type"):
        op.add_column(
            "red_packets",
            sa.Column("content_type", sa.String(length=20), server_default="url", nullable=False),
        )
    if not has_col("red_packets", "content_value"):
        op.add_column(
            "red_packets", sa.Column("content_value", sa.Text(), server_default="", nullable=False)
        )
    if not has_col("red_packets", "content_image_url"):
        op.add_column(
            "red_packets",
            sa.Column(
                "content_image_url", sa.String(length=500), server_default="", nullable=False
            ),
        )
    if not has_col("red_packets", "content_image_key"):
        op.add_column(
            "red_packets",
            sa.Column(
                "content_image_key", sa.String(length=255), server_default="", nullable=False
            ),
        )
    if not has_col("red_packets", "meta_json"):
        op.add_column(
            "red_packets", sa.Column("meta_json", sa.Text(), server_default="{}", nullable=False)
        )

    red_packet_indexes = {idx["name"] for idx in inspector.get_indexes("red_packets")}
    if "ix_red_packets_category_id" not in red_packet_indexes:
        op.create_index("ix_red_packets_category_id", "red_packets", ["category_id"], unique=False)

    if has_col("red_packets", "claim_url"):
        op.execute(
            """
            UPDATE red_packets
            SET content_value = claim_url
            WHERE (content_value = '' OR content_value IS NULL) AND claim_url <> ''
            """
        )

    if not has_table("red_packet_categories"):
        op.create_table(
            "red_packet_categories",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=60), nullable=False),
            sa.Column("code", sa.String(length=60), nullable=False),
            sa.Column("is_builtin", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column(
                "allowed_content_types", sa.String(length=60), server_default="url", nullable=False
            ),
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
            sa.PrimaryKeyConstraint("id", name="pk_red_packet_categories"),
            sa.UniqueConstraint("name", name="uq_red_packet_categories_name"),
            sa.UniqueConstraint("code", name="uq_red_packet_categories_code"),
        )
        op.create_index(
            "ix_red_packet_categories_name", "red_packet_categories", ["name"], unique=True
        )
        op.create_index(
            "ix_red_packet_categories_code", "red_packet_categories", ["code"], unique=True
        )

    if not has_table("red_packet_tags"):
        op.create_table(
            "red_packet_tags",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
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
            sa.PrimaryKeyConstraint("id", name="pk_red_packet_tags"),
            sa.UniqueConstraint("name", name="uq_red_packet_tags_name"),
        )
        op.create_index("ix_red_packet_tags_name", "red_packet_tags", ["name"], unique=True)

    if not has_table("red_packet_tag_bindings"):
        op.create_table(
            "red_packet_tag_bindings",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("red_packet_id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
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
                ["red_packet_id"],
                ["red_packets.id"],
                name="fk_red_packet_tag_bindings_red_packet_id_red_packets",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["tag_id"],
                ["red_packet_tags.id"],
                name="fk_red_packet_tag_bindings_tag_id_red_packet_tags",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_red_packet_tag_bindings"),
            sa.UniqueConstraint("red_packet_id", "tag_id", name="uq_red_packet_tag_pair"),
        )
        op.create_index(
            "ix_red_packet_tag_bindings_red_packet_id",
            "red_packet_tag_bindings",
            ["red_packet_id"],
            unique=False,
        )
        op.create_index(
            "ix_red_packet_tag_bindings_tag_id", "red_packet_tag_bindings", ["tag_id"], unique=False
        )

    op.execute(
        """
        INSERT OR IGNORE INTO red_packet_categories (name, code, is_builtin, allowed_content_types)
        VALUES
          ('支付宝红包', 'alipay_red_packet', 1, 'url'),
          ('账号', 'account', 1, 'text'),
          ('其他', 'misc', 1, 'url,text,qr_image')
        """
    )
    op.execute(
        """
        UPDATE red_packets
        SET category_id = (
            SELECT id FROM red_packet_categories WHERE code = 'misc' LIMIT 1
        )
        WHERE category_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_red_packet_tag_bindings_tag_id", table_name="red_packet_tag_bindings")
    op.drop_index("ix_red_packet_tag_bindings_red_packet_id", table_name="red_packet_tag_bindings")
    op.drop_table("red_packet_tag_bindings")
    op.drop_index("ix_red_packet_tags_name", table_name="red_packet_tags")
    op.drop_table("red_packet_tags")
    op.drop_index("ix_red_packet_categories_code", table_name="red_packet_categories")
    op.drop_index("ix_red_packet_categories_name", table_name="red_packet_categories")
    op.drop_table("red_packet_categories")

    op.drop_index("ix_red_packets_category_id", table_name="red_packets")
    op.drop_column("red_packets", "meta_json")
    op.drop_column("red_packets", "content_image_key")
    op.drop_column("red_packets", "content_image_url")
    op.drop_column("red_packets", "content_value")
    op.drop_column("red_packets", "content_type")
    op.drop_column("red_packets", "category_id")
    op.drop_column("red_packets", "title")
