from datetime import date, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_main_db, get_temp_db
from app.models import Allocation, BlockStatus, Demand, ExtensionStatus, Project, ProjectStatus, RequestStatus, Resource, ResourceBlock, User, UserRole
from app.schemas.forms import DemandCreate
from app.services.resource_service import ResourceMatchingService, searchable_resources
from app.services.block_service import ResourceBlockService, booking_calendars

router = APIRouter(prefix="/lead")
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(require_role(UserRole.PROJECT_LEAD)), db: Session = Depends(get_temp_db)):
    projects = db.query(Project).filter(Project.lead_id == user.id).all()
    demands = db.query(Demand).filter(Demand.requested_by_id == user.id).order_by(Demand.created_at.desc()).limit(8).all()
    available = db.query(Resource).filter(Resource.current_allocation < 100).order_by(Resource.current_allocation).limit(8).all()
    extension_items = extension_query(db, user.id).limit(6).all()
    return templates.TemplateResponse("lead/dashboard.html", {"request": request, "user": user, "projects": projects, "demands": demands, "available": available, "extension_items": extension_items})


@router.get("/raise-demand", response_class=HTMLResponse)
def raise_demand_page(request: Request, user: User = Depends(require_role(UserRole.PROJECT_LEAD)), db: Session = Depends(get_temp_db)):
    projects = db.query(Project).filter(Project.lead_id == user.id).all()
    return templates.TemplateResponse("lead/raise_demand.html", {"request": request, "user": user, "projects": projects, "errors": [], "today": date.today()})


@router.post("/raise-demand")
def raise_demand(
    request: Request,
    project_id: int = Form(...),
    required_skill: str = Form(...),
    required_role: str = Form(...),
    required_level: int = Form(...),
    number_of_resources: int = Form(...),
    allocation_percent: int = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    priority: str = Form(...),
    remarks: str | None = Form(None),
    user: User = Depends(require_role(UserRole.PROJECT_LEAD)),
    db: Session = Depends(get_temp_db),
):
    try:
        data = DemandCreate(
            project_id=project_id,
            required_skill=required_skill,
            required_role=required_role,
            required_level=required_level,
            number_of_resources=number_of_resources,
            allocation_percent=allocation_percent,
            start_date=start_date,
            end_date=end_date,
            priority=priority,
            remarks=remarks,
        )
    except ValidationError as exc:
        projects = db.query(Project).filter(Project.lead_id == user.id).all()
        return templates.TemplateResponse("lead/raise_demand.html", {"request": request, "user": user, "projects": projects, "errors": [e["msg"] for e in exc.errors()], "today": date.today()}, status_code=400)
    demand = ResourceMatchingService(db).create_demand(**data.model_dump(), requested_by_id=user.id)
    return RedirectResponse(f"/lead/demands/{demand.id}/recommendations", status_code=303)


@router.get("/demands/{demand_id}/recommendations", response_class=HTMLResponse)
def recommendations(demand_id: int, request: Request, user: User = Depends(require_role(UserRole.PROJECT_LEAD)), db: Session = Depends(get_temp_db)):
    demand = db.get(Demand, demand_id)
    if not demand or demand.requested_by_id != user.id:
        return RedirectResponse("/lead/dashboard", status_code=303)
    return templates.TemplateResponse("lead/recommendations.html", {"request": request, "user": user, "demand": demand})


@router.post("/demands/{demand_id}/submit")
def submit_selection(demand_id: int, resource_ids: list[int] = Form(...), user: User = Depends(require_role(UserRole.PROJECT_LEAD)), db: Session = Depends(get_temp_db)):
    demand = db.get(Demand, demand_id)
    if not demand or demand.requested_by_id != user.id:
        return RedirectResponse("/lead/dashboard", status_code=303)
    ResourceMatchingService(db).reserve_resources(demand_id, resource_ids)
    return RedirectResponse("/lead/requests", status_code=303)


@router.get("/resources", response_class=HTMLResponse)
def resources(request: Request, search: str | None = None, skill: str | None = None, allocation_max: int | None = None, availability_start: date | None = None, availability_end: date | None = None, user: User = Depends(require_role(UserRole.PROJECT_LEAD)), db: Session = Depends(get_temp_db)):
    query = searchable_resources(db, search, skill)
    if allocation_max is not None:
        query = query.filter(Resource.current_allocation + Resource.reserved_allocation <= allocation_max)
    resources = query.all()
    if availability_start and availability_end and availability_end >= availability_start:
        service = ResourceBlockService(None, db)
        resources = [resource for resource in resources if service.is_free(resource.id, availability_start, availability_end)]
    skills = [row[0] for row in db.query(Resource.skill).distinct().order_by(Resource.skill).all()]
    calendars = booking_calendars(resources)
    projects = db.query(Project).filter(Project.lead_id == user.id, Project.status == ProjectStatus.ACTIVE).all()
    return templates.TemplateResponse("lead/resources.html", {"request": request, "user": user, "resources": resources, "search": search or "", "skill": skill or "", "skills": skills, "projects": projects, "calendars": calendars, "today": date.today(), "allocation_max": allocation_max, "availability_start": availability_start, "availability_end": availability_end, "message": request.query_params.get("message"), "error": request.query_params.get("error")})


@router.post("/resources/{resource_id}/block")
def block_resource(
    resource_id: int,
    start_date: date = Form(...),
    end_date: date = Form(...),
    project_id: str = Form(""),
    reason: str | None = Form(None),
    user: User = Depends(require_role(UserRole.PROJECT_LEAD)),
    db: Session = Depends(get_temp_db),
):
    try:
        parsed_project_id = int(project_id) if project_id.strip() else None
        ResourceBlockService(None, db).request(resource_id, user, start_date, end_date, parsed_project_id, reason)
    except ValueError as exc:
        return RedirectResponse(f"/lead/resources?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/lead/resources?message=block-requested", status_code=303)


@router.post("/resources/{resource_id}/request-cv")
def request_resource_cv(resource_id: int, message: str | None = Form(None), user: User = Depends(require_role(UserRole.PROJECT_LEAD)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    main_resource = main_db.get(Resource, resource_id)
    temp_resource = temp_db.get(Resource, resource_id)
    if not main_resource:
        return RedirectResponse("/lead/resources?error=Resource+not+found", status_code=303)
    for resource in (main_resource, temp_resource):
        if resource:
            resource.cv_requested = True
            resource.cv_request_message = message or f"{user.full_name} requested your latest CV."
            resource.cv_requested_at = datetime.utcnow()
    main_db.commit()
    temp_db.commit()
    return RedirectResponse("/lead/resources?message=cv-requested", status_code=303)


@router.get("/requests", response_class=HTMLResponse)
def requests_page(request: Request, user: User = Depends(require_role(UserRole.PROJECT_LEAD)), db: Session = Depends(get_temp_db)):
    demands = db.query(Demand).filter(Demand.requested_by_id == user.id).order_by(Demand.created_at.desc()).all()
    return templates.TemplateResponse("lead/requests.html", {"request": request, "user": user, "demands": demands})


@router.get("/my-resources", response_class=HTMLResponse)
def my_resources_page(request: Request, user: User = Depends(require_role(UserRole.PROJECT_LEAD)), db: Session = Depends(get_temp_db)):
    allocations = (
        db.query(Allocation).join(Project, Allocation.project_id == Project.id)
        .filter(Project.lead_id == user.id, Allocation.status == "Active")
        .order_by(Allocation.end_date.asc()).all()
    )
    blocks = db.query(ResourceBlock).filter(ResourceBlock.requested_by_id == user.id).order_by(ResourceBlock.created_at.desc()).all()
    return templates.TemplateResponse("lead/my_resources.html", {"request": request, "user": user, "allocations": allocations, "blocks": blocks, "today": date.today(), "message": request.query_params.get("message")})


@router.get("/extensions")
def extensions_redirect(user: User = Depends(require_role(UserRole.PROJECT_LEAD))):
    return RedirectResponse("/lead/my-resources", status_code=303)


@router.post("/my-resources/{allocation_id}/extension")
def update_extension_status(
    allocation_id: int,
    extension_status: ExtensionStatus = Form(...),
    extension_remarks: str | None = Form(None),
    user: User = Depends(require_role(UserRole.PROJECT_LEAD)),
    db: Session = Depends(get_temp_db),
):
    allocation = db.get(Allocation, allocation_id)
    if not allocation or allocation.project.lead_id != user.id:
        return RedirectResponse("/lead/my-resources", status_code=303)
    allocation.extension_status = extension_status
    allocation.extension_remarks = extension_remarks
    db.commit()
    return RedirectResponse("/lead/my-resources?message=updated", status_code=303)


def extension_query(db: Session, lead_id: int):
    return (
        db.query(Allocation)
        .join(Project, Allocation.project_id == Project.id)
        .filter(Project.lead_id == lead_id, Allocation.extension_status != ExtensionStatus.NOT_DUE)
        .order_by(Project.end_date.asc(), Allocation.extension_status.desc())
    )
