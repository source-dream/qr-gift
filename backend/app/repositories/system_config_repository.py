from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig


class SystemConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[SystemConfig]:
        stmt = select(SystemConfig).order_by(SystemConfig.config_key.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_key(self, key: str) -> SystemConfig | None:
        stmt = select(SystemConfig).where(SystemConfig.config_key == key)
        return self.db.scalar(stmt)

    def upsert(self, key: str, value: str, is_secret: bool) -> SystemConfig:
        config = self.get_by_key(key)
        if not config:
            config = SystemConfig(config_key=key, config_value=value, is_secret=is_secret)
            self.db.add(config)
            return config
        config.config_value = value
        config.is_secret = is_secret
        return config
