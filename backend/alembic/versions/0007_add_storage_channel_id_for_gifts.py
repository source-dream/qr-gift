"""add storage channel id for gift qrcodes

Revision ID: 0007_add_storage_channel_id_for_gifts
Revises: 0006_add_plain_token_for_gifts
Create Date: 2026-02-16 03:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0007_add_storage_channel_id_for_gifts"
down_revision: str | None = "0006_add_plain_token_for_gifts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("gift_qrcodes")}
    if "storage_channel_id" not in columns:
        op.add_column(
            "gift_qrcodes",
            sa.Column(
                "storage_channel_id", sa.String(length=64), server_default="", nullable=False
            ),
        )


def downgrade() -> None:
    op.drop_column("gift_qrcodes", "storage_channel_id")
