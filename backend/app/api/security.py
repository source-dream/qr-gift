from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.models.user import User
from app.schemas.security import SecurityRulePayload, SecurityRuleResponse
from app.services.security_service import SecurityService

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/rules")
def get_rules(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    rules = SecurityService(db).get_rules()
    return ok(SecurityRuleResponse(rules=rules).model_dump())


@router.put("/rules")
def update_rules(
    payload: SecurityRulePayload,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    rules = SecurityService(db).update_rules(data)
    return ok(SecurityRuleResponse(rules=rules).model_dump(), "更新成功")
