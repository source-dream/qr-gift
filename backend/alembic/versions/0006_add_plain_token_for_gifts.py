"""add plain token for gift qrcodes

Revision ID: 0006_add_plain_token_for_gifts
Revises: 0005_red_packet_content_and_taxonomy
Create Date: 2026-02-16 02:05:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0006_add_plain_token_for_gifts"
down_revision: str | None = "0005_red_packet_content_and_taxonomy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("gift_qrcodes")}
    if "token_plain" not in columns:
        op.add_column(
            "gift_qrcodes",
            sa.Column("token_plain", sa.String(length=128), server_default="", nullable=False),
        )

    indexes = {idx["name"] for idx in inspector.get_indexes("gift_qrcodes")}
    if "ix_gift_qrcodes_token_plain" not in indexes:
        op.create_index(
            "ix_gift_qrcodes_token_plain", "gift_qrcodes", ["token_plain"], unique=False
        )


def downgrade() -> None:
    op.drop_index("ix_gift_qrcodes_token_plain", table_name="gift_qrcodes")
    op.drop_column("gift_qrcodes", "token_plain")
