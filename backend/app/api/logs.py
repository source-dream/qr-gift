from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.models.gift import GiftClaimLog
from app.models.log import AccessLog, OperationLog
from app.models.user import User
from app.schemas.logs import AccessLogItem, GiftClaimLogItem, OperationLogItem

router = APIRouter(prefix="/api/logs", tags=["logs"])


def _normalize_keyword(q: str) -> str:
    return q.strip()


@router.get("/access")
def list_access_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str = Query(default=""),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    keyword = _normalize_keyword(q)
    stmt = select(AccessLog)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                AccessLog.source.ilike(pattern),
                AccessLog.path.ilike(pattern),
                AccessLog.method.ilike(pattern),
                AccessLog.ip.ilike(pattern),
                cast(AccessLog.status_code, String).ilike(pattern),
            )
        )

    rows = list(db.scalars(stmt.order_by(AccessLog.id.desc()).offset(offset).limit(limit)).all())
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
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str = Query(default=""),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    keyword = _normalize_keyword(q)
    stmt = select(GiftClaimLog)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                cast(GiftClaimLog.gift_qrcode_id, String).ilike(pattern),
                cast(GiftClaimLog.red_packet_id, String).ilike(pattern),
                GiftClaimLog.dispatch_strategy.ilike(pattern),
                GiftClaimLog.ip.ilike(pattern),
                GiftClaimLog.result.ilike(pattern),
                GiftClaimLog.reason.ilike(pattern),
            )
        )

    rows = list(db.scalars(stmt.order_by(GiftClaimLog.id.desc()).offset(offset).limit(limit)).all())
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
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str = Query(default=""),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    keyword = _normalize_keyword(q)
    stmt = select(OperationLog)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                cast(OperationLog.user_id, String).ilike(pattern),
                OperationLog.action.ilike(pattern),
                OperationLog.detail.ilike(pattern),
            )
        )

    rows = list(db.scalars(stmt.order_by(OperationLog.id.desc()).offset(offset).limit(limit)).all())
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
