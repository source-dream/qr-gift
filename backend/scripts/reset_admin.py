"""本地重置或创建管理员账号。"""

from __future__ import annotations

import argparse
import getpass

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="重置管理员密码")
    parser.add_argument("--username", default="admin", help="管理员用户名，默认 admin")
    parser.add_argument("--password", default="", help="管理员密码，不传则交互输入")
    return parser.parse_args()


def resolve_password(raw: str) -> str:
    if raw:
        return raw

    password = getpass.getpass("请输入新密码(至少8位): ").strip()
    confirm = getpass.getpass("请再次输入新密码: ").strip()
    if password != confirm:
        raise ValueError("两次密码输入不一致")
    if len(password) < 8:
        raise ValueError("密码长度不能少于8位")
    return password


def run(username: str, password: str) -> None:
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        hashed = get_password_hash(password)
        if user:
            user.password_hash = hashed
            user.role = "admin"
            user.is_active = True
            db.commit()
            print(f"管理员密码重置成功: {username}")
            return

        db.add(User(username=username, password_hash=hashed, role="admin", is_active=True))
        db.commit()
        print(f"管理员创建成功: {username}")
    finally:
        db.close()


if __name__ == "__main__":
    args = parse_args()
    final_password = resolve_password(args.password)
    run(args.username, final_password)
