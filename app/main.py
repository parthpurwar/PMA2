from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth, employee, lead, pmo, profile
from app.core.config import get_settings
from app.db.init_db import initialize_databases

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie=settings.session_cookie)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(pmo.router)
app.include_router(lead.router)
app.include_router(employee.router)
app.include_router(profile.router)


@app.on_event("startup")
def startup() -> None:
    initialize_databases()


@app.exception_handler(401)
def unauthorized(request: Request, exc):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(403)
def forbidden(request: Request, exc):
    return RedirectResponse("/login", status_code=303)
