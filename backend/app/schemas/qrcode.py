from pydantic import BaseModel, Field


class CreateBatchRequest(BaseModel):
    amount: int = Field(gt=0, le=5000)


class QrcodeItem(BaseModel):
    id: int
    short_code: str
    status: str
    image_url: str


class QrcodeBatchResponse(BaseModel):
    batch_no: str
    amount: int
