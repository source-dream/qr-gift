import json
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.security_repository import SecurityRepository

DEFAULT_RULES: dict[str, Any] = {
    "claim_enabled": True,
    "ip_whitelist": [],
    "ip_blacklist": [],
    "max_per_ip_per_hour": 5,
}


class SecurityService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SecurityRepository(db)

    def get_rules(self) -> dict[str, Any]:
        # 中文注释：先加载默认规则，再用数据库配置覆盖，确保新部署也有可用安全基线。
        merged = dict(DEFAULT_RULES)
        for item in self.repo.list_rules():
            merged[item.rule_key] = self._parse(item.rule_value)
        return merged

    def update_rules(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.get_rules()
        for key, value in payload.items():
            if key not in DEFAULT_RULES:
                continue
            # 中文注释：规则值统一以 JSON 文本存储，便于兼容布尔、数字与列表类型。
            current[key] = value
            self.repo.upsert_rule(key, json.dumps(value, ensure_ascii=False))

        self.db.commit()
        return current

    @staticmethod
    def _parse(raw: str) -> Any:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
