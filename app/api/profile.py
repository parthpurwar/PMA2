from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import login_required
from app.db.session import get_main_db
from app.models import Resource, User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/employees/{resource_id}", response_class=HTMLResponse)
def employee_profile(resource_id: int, request: Request, user: User = Depends(login_required), db: Session = Depends(get_main_db)):
    resource = db.get(Resource, resource_id)
    if not resource or not resource.is_active:
        return RedirectResponse("/", status_code=303)
    active_allocations = [allocation for allocation in resource.allocations if allocation.status == "Active"]
    past_allocations = [allocation for allocation in resource.allocations if allocation.status != "Active"]
    return templates.TemplateResponse("shared/employee_profile.html", {"request": request, "user": user, "resource": resource, "active_allocations": active_allocations, "past_allocations": past_allocations})
