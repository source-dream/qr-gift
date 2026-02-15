from pydantic import BaseModel, Field


class ManualBindRequest(BaseModel):
    qrcode_id: int = Field(gt=0)
    red_packet_id: int = Field(gt=0)


class AutoBindRequest(BaseModel):
    count: int = Field(gt=0, le=5000)
