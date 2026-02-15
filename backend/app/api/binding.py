from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.models.user import User
from app.schemas.binding import AutoBindRequest, ManualBindRequest
from app.services.binding_service import BindingService

router = APIRouter(prefix="/api/bindings", tags=["bindings"])


@router.post("/manual")
def bind_manual(
    payload: ManualBindRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    try:
        BindingService(db).bind_manual(payload.qrcode_id, payload.red_packet_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(message="绑定成功")


@router.post("/auto")
def bind_auto(
    payload: AutoBindRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    amount = BindingService(db).bind_auto(payload.count)
    return ok({"bound_count": amount}, "自动绑定完成")
