from datetime import datetime

from pydantic import BaseModel, Field


class CreateGiftRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    activate_at: datetime | None = None
    expire_at: datetime | None = None
    binding_mode: str = Field(default="manual", pattern="^(manual|auto)$")
    dispatch_strategy: str = Field(default="random", pattern="^(amount_desc|level_desc|random)$")
    red_packet_ids: list[int] = Field(default_factory=list)
    style_type: str = Field(default="festival", max_length=30)


class UpdateGiftRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    activate_at: datetime | None = None
    expire_at: datetime | None = None
    binding_mode: str = Field(default="manual", pattern="^(manual|auto)$")
    dispatch_strategy: str = Field(default="random", pattern="^(amount_desc|level_desc|random)$")
    red_packet_ids: list[int] = Field(default_factory=list)
    style_type: str = Field(default="festival", max_length=30)


class GiftItem(BaseModel):
    id: int
    title: str
    status: str
    activate_at: datetime | None
    expire_at: datetime | None
    binding_mode: str
    dispatch_strategy: str
    binding_count: int
    style_type: str
    image_url: str
    claim_url: str


class CreateGiftResponse(BaseModel):
    id: int
    title: str
    claim_url: str


class GiftDetail(BaseModel):
    id: int
    title: str
    status: str
    activate_at: datetime | None
    expire_at: datetime | None
    binding_mode: str
    dispatch_strategy: str
    style_type: str
    image_url: str
    claim_url: str
    red_packet_ids: list[int]
