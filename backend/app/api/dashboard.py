from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.models.gift import GiftBinding, GiftClaimLog, GiftQrcode
from app.models.red_packet import RedPacket
from app.models.user import User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    total_gifts = db.query(func.count(GiftQrcode.id)).scalar() or 0
    total_red_packets = db.query(func.count(RedPacket.id)).scalar() or 0
    total_bound = (
        db.query(func.count(GiftBinding.id)).filter(GiftBinding.status == "active").scalar() or 0
    )
    total_claimed = (
        db.query(func.count(GiftQrcode.id)).filter(GiftQrcode.status == "claimed").scalar() or 0
    )
    today_success = (
        db.query(func.count(GiftClaimLog.id))
        .filter(
            GiftClaimLog.result == "success", func.date(GiftClaimLog.created_at) == date.today()
        )
        .scalar()
        or 0
    )
    today_rejected = (
        db.query(func.count(GiftClaimLog.id))
        .filter(
            GiftClaimLog.result == "rejected", func.date(GiftClaimLog.created_at) == date.today()
        )
        .scalar()
        or 0
    )
    return ok(
        {
            "total_gifts": total_gifts,
            "total_red_packets": total_red_packets,
            "total_bound": total_bound,
            "total_claimed": total_claimed,
            "today_success_claims": today_success,
            "today_rejected_claims": today_rejected,
        }
    )


@router.get("/trend-7d")
def trend_7d(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    today = date.today()
    start_date = today - timedelta(days=6)

    rows = (
        db.query(
            func.date(GiftClaimLog.created_at).label("day"),
            GiftClaimLog.result,
            func.count(GiftClaimLog.id).label("count"),
        )
        .filter(func.date(GiftClaimLog.created_at) >= start_date)
        .group_by(func.date(GiftClaimLog.created_at), GiftClaimLog.result)
        .all()
    )

    days = [(start_date + timedelta(days=i)).isoformat() for i in range(7)]
    success_map = {day: 0 for day in days}
    rejected_map = {day: 0 for day in days}

    for day, result, count in rows:
        day_str = str(day)
        if day_str not in success_map:
            continue
        if result == "success":
            success_map[day_str] = int(count)
        elif result == "rejected":
            rejected_map[day_str] = int(count)

    return ok(
        {
            "days": days,
            "success": [success_map[day] for day in days],
            "rejected": [rejected_map[day] for day in days],
        }
    )
