from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    BootstrapStatusResponse,
    LoginRequest,
    LoginResponse,
    SetupRequest,
    SetupResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user_repo = UserRepository(db)
    if user_repo.count_all() == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统尚未初始化，请先创建管理员")

    user = user_repo.get_by_username(payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    token = create_access_token(subject=str(user.id), role=user.role)
    return ok(LoginResponse(access_token=token).model_dump())


@router.get("/bootstrap-status")
def bootstrap_status(db: Session = Depends(get_db)) -> dict:
    initialized = UserRepository(db).count_all() > 0
    return ok(BootstrapStatusResponse(initialized=initialized).model_dump())


@router.post("/setup")
def setup(payload: SetupRequest, db: Session = Depends(get_db)) -> dict:
    user_repo = UserRepository(db)
    if user_repo.count_all() > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="系统已初始化，请使用重置命令修改管理员密码")

    # 中文注释：首次初始化只允许创建一个管理员，后续账号管理走后台权限体系。
    user = user_repo.create_admin(username=payload.username, password_hash=get_password_hash(payload.password))
    db.commit()
    response = SetupResponse(user_id=user.id, username=user.username)
    return ok(response.model_dump(), "初始化成功")


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict:
    return ok(
        {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
        }
    )
