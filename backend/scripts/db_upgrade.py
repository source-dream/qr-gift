"""统一数据库迁移入口，兼容旧版本直接建表场景。"""

from __future__ import annotations

from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings

MANAGED_TABLES = {
    "users",
    "qrcode_batches",
    "qrcodes",
    "red_packet_batches",
    "red_packets",
    "bindings",
    "claim_logs",
    "operation_logs",
    "security_rules",
}


def build_alembic_config() -> Config:
    base_dir = Path(__file__).resolve().parents[1]
    config = Config(str(base_dir / "alembic.ini"))
    config.set_main_option("script_location", str(base_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", get_settings().sqlite_url)
    return config


def has_legacy_initialized_schema() -> bool:
    settings = get_settings()
    engine = create_engine(settings.sqlite_url, connect_args={"check_same_thread": False})
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    engine.dispose()

    has_version_table = "alembic_version" in table_names
    has_business_tables = bool(table_names & MANAGED_TABLES)
    return has_business_tables and not has_version_table


def has_empty_version_state() -> bool:
    settings = get_settings()
    db_path = settings.sqlite_url.replace("sqlite:///", "", 1)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        )
        has_table = cursor.fetchone()[0] > 0
        if not has_table:
            return False

        cursor.execute("SELECT count(*) FROM alembic_version")
        row_count = cursor.fetchone()[0]
        return row_count == 0
    finally:
        conn.close()


def run() -> None:
    config = build_alembic_config()

    if has_legacy_initialized_schema() or has_empty_version_state():
        # 中文注释：兼容两类历史库：1) 已有业务表但无 alembic_version；2) alembic_version 表存在但无版本记录。
        command.stamp(config, "0001_init_tables")

    command.upgrade(config, "head")
    print("数据库迁移完成")


if __name__ == "__main__":
    run()
