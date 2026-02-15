from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.db.scalar(stmt)

    def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return self.db.scalar(stmt)

    def count_all(self) -> int:
        stmt = select(func.count(User.id))
        return self.db.scalar(stmt) or 0

    def create_admin(self, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash, role="admin", is_active=True)
        self.db.add(user)
        self.db.flush()
        return user
