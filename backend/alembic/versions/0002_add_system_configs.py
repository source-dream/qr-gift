"""add system configs table

Revision ID: 0002_add_system_configs
Revises: 0001_init_tables
Create Date: 2026-02-15 21:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_system_configs"
down_revision: str | None = "0001_init_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("config_key", sa.String(length=120), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id", name="pk_system_configs"),
        sa.UniqueConstraint("config_key", name="uq_system_configs_config_key"),
    )
    op.create_index("ix_system_configs_config_key", "system_configs", ["config_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_system_configs_config_key", table_name="system_configs")
    op.drop_table("system_configs")
