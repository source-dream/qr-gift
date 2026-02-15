from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.models.gift import GiftClaimLog
from app.models.log import AccessLog, OperationLog
from app.models.user import User
from app.schemas.logs import AccessLogItem, GiftClaimLogItem, OperationLogItem

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/access")
def list_access_logs(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    rows = list(db.scalars(select(AccessLog).order_by(AccessLog.id.desc()).limit(200)).all())
    data = [
        AccessLogItem(
            id=row.id,
            source=row.source,
            path=row.path,
            method=row.method,
            ip=row.ip,
            status_code=row.status_code,
            latency_ms=row.latency_ms,
            created_at=row.created_at,
        ).model_dump()
        for row in rows
    ]
    return ok(data)


@router.get("/claims")
def list_claim_logs(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    rows = list(db.scalars(select(GiftClaimLog).order_by(GiftClaimLog.id.desc()).limit(200)).all())
    data = [
        GiftClaimLogItem(
            id=row.id,
            gift_qrcode_id=row.gift_qrcode_id,
            red_packet_id=row.red_packet_id,
            dispatch_strategy=row.dispatch_strategy,
            ip=row.ip,
            result=row.result,
            reason=row.reason,
            created_at=row.created_at,
        ).model_dump()
        for row in rows
    ]
    return ok(data)


@router.get("/operations")
def list_operation_logs(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    rows = list(db.scalars(select(OperationLog).order_by(OperationLog.id.desc()).limit(200)).all())
    data = [
        OperationLogItem(
            id=row.id,
            user_id=row.user_id,
            action=row.action,
            detail=row.detail,
            created_at=row.created_at,
        ).model_dump()
        for row in rows
    ]
    return ok(data)
