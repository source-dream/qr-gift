from datetime import datetime

from pydantic import BaseModel, Field


class RedPacketCategoryItem(BaseModel):
    id: int
    name: str
    code: str
    is_builtin: bool
    allowed_content_types: list[str]


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class CreateRedPacketRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    amount: float = 0
    level: int = Field(default=1, ge=1, le=10)
    category_code: str | None = Field(default=None, max_length=60)
    custom_category_name: str | None = Field(default=None, max_length=60)
    content_type: str = Field(pattern="^(url|text|qr_image)$")
    content_value: str = ""
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, str] = Field(default_factory=dict)
    available_from: datetime | None = None
    available_to: datetime | None = None


class UpdateRedPacketRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    amount: float = 0
    level: int = Field(default=1, ge=1, le=10)
    content_value: str = ""
    available_from: datetime | None = None
    available_to: datetime | None = None


class RedPacketItem(BaseModel):
    id: int
    title: str
    amount: float
    level: int
    category_name: str
    category_code: str
    tags: list[str]
    content_type: str
    content_value: str
    content_image_url: str
    status: str
    meta: dict[str, str]
    available_from: datetime | None
    available_to: datetime | None


class RedPacketImportResponse(BaseModel):
    batch_no: str
    imported_count: int


class ParseImageResult(BaseModel):
    filename: str
    status: str
    decoded_url: str


class ParseImagesResponse(BaseModel):
    success_count: int
    failed_count: int
    results: list[ParseImageResult]


class BatchUrlItem(BaseModel):
    filename: str = ""
    url: str = Field(min_length=1, max_length=1200)


class BatchImportUrlsRequest(BaseModel):
    title_prefix: str = Field(default="支付宝红包", max_length=120)
    amount: float = 0
    level: int = Field(default=1, ge=1, le=10)
    category_code: str | None = Field(default="alipay_red_packet", max_length=60)
    tags: list[str] = Field(default_factory=list)
    available_from: datetime | None = None
    available_to: datetime | None = None
    urls: list[BatchUrlItem] = Field(default_factory=list)
