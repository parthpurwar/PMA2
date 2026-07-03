from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import User


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    def get_user(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)
