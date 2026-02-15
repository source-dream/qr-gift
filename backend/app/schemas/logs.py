from datetime import datetime

from pydantic import BaseModel


class AccessLogItem(BaseModel):
    id: int
    source: str
    path: str
    method: str
    ip: str
    status_code: int
    latency_ms: int
    created_at: datetime


class GiftClaimLogItem(BaseModel):
    id: int
    gift_qrcode_id: int
    red_packet_id: int | None
    dispatch_strategy: str
    ip: str
    result: str
    reason: str
    created_at: datetime


class OperationLogItem(BaseModel):
    id: int
    user_id: int | None
    action: str
    detail: str
    created_at: datetime
