import ipaddress
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SecurityRulePayload(BaseModel):
    claim_enabled: bool | None = None
    ip_whitelist: list[str] | None = None
    ip_blacklist: list[str] | None = None
    max_per_ip_per_hour: int | None = Field(default=None, ge=1, le=1000)

    @field_validator("ip_whitelist", "ip_blacklist")
    @classmethod
    def validate_ip_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value

        normalized: list[str] = []
        for item in value:
            raw = item.strip()
            if not raw:
                continue
            # 中文注释：安全策略仅接受标准 IPv4/IPv6 字符串，防止无效配置导致规则失效。
            try:
                ipaddress.ip_address(raw)
            except ValueError as exc:
                raise ValueError(f"无效 IP 地址: {raw}") from exc
            normalized.append(raw)
        return normalized


class SecurityRuleResponse(BaseModel):
    rules: dict[str, Any]
