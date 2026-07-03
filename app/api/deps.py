from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_main_db
from app.models import User, UserRole
from app.services.auth_service import AuthService


def current_user(request: Request, db: Annotated[Session, Depends(get_main_db)]) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return AuthService(db).get_user(int(user_id))


def login_required(user: Annotated[User | None, Depends(current_user)]) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return user


def require_role(role: UserRole):
    def dependency(user: Annotated[User, Depends(login_required)]) -> User:
        if user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return user

    return dependency


def redirect_for_role(user: User) -> RedirectResponse:
    if user.role == UserRole.PMO:
        path = "/pmo/dashboard"
    elif user.role == UserRole.PROJECT_LEAD:
        path = "/lead/dashboard"
    else:
        path = "/employee/dashboard"
    return RedirectResponse(path, status_code=303)
