from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.core.response import ok
from app.models.user import User
from app.schemas.system_config import (
    ClaimContactUpdateRequest,
    StorageConfigTestRequest,
    StorageConfigUpdateRequest,
)
from app.services.system_config_service import SystemConfigService

router = APIRouter(prefix="/api/system", tags=["system-config"])


@router.get("/storage-config")
def get_storage_config(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_admin),
) -> dict:
    data = SystemConfigService(db).get_storage_config()
    return ok(data.model_dump())


@router.put("/storage-config")
def update_storage_config(
    payload: StorageConfigUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
) -> dict:
    try:
        data = SystemConfigService(db).update_storage_config(payload=payload, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(data.model_dump(), "保存成功")


@router.post("/storage-config/test")
def test_storage_config(
    payload: StorageConfigTestRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_admin),
) -> dict:
    try:
        SystemConfigService(db).test_storage_config(payload)
    except Exception as exc:
        detail = str(exc)
        if "InvalidAccessKeyId" in detail:
            detail = (
                "连接测试失败: AccessKey ID 无效，请确认使用的是 RAM 用户的 OSS AccessKey，"
                "并且未粘贴错误或过期密钥。"
            )
        else:
            detail = f"连接测试失败: {detail}"
        raise HTTPException(status_code=400, detail=detail) from exc
    return ok(message="连接测试通过")


@router.get("/claim-contact")
def get_claim_contact(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_admin),
) -> dict:
    data = SystemConfigService(db).get_claim_contact()
    return ok(data.model_dump())


@router.put("/claim-contact")
def update_claim_contact(
    payload: ClaimContactUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
) -> dict:
    try:
        data = SystemConfigService(db).update_claim_contact(payload.contact_text, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(data.model_dump(), "保存成功")
