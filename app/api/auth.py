from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import current_user, redirect_for_role
from app.db.session import get_main_db
from app.services.auth_service import AuthService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user=Depends(current_user)):
    if user:
        return redirect_for_role(user)
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": None})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_main_db)):
    user = AuthService(db).authenticate(username.strip(), password)
    if not user:
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": "Invalid username or password."}, status_code=400)
    request.session["user_id"] = user.id
    request.session["role"] = user.role.value
    return redirect_for_role(user)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
