from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.log import SecurityRule


class SecurityRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_rules(self) -> list[SecurityRule]:
        stmt = select(SecurityRule).order_by(SecurityRule.rule_key.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_key(self, key: str) -> SecurityRule | None:
        stmt = select(SecurityRule).where(SecurityRule.rule_key == key)
        return self.db.scalar(stmt)

    def upsert_rule(self, key: str, value: str) -> SecurityRule:
        rule = self.get_by_key(key)
        if not rule:
            rule = SecurityRule(rule_key=key, rule_value=value)
            self.db.add(rule)
            return rule
        rule.rule_value = value
        return rule
