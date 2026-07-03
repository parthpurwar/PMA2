from datetime import date, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.security import hash_password
from app.db.session import get_main_db, get_temp_db
from app.models import AuditLog, BlockStatus, Demand, Project, RequestStatus, Resource, ResourceBlock, SyncLog, User, UserRole
from app.services.approval_service import ApprovalService
from app.services.report_service import ReportService
from app.services.sync_service import SyncService
from app.services.block_service import ResourceBlockService
from app.services.cv_service import save_cv

router = APIRouter(prefix="/pmo")
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(require_role(UserRole.PMO)), temp_db: Session = Depends(get_temp_db)):
    metrics = ReportService(temp_db).dashboard_metrics()
    latest_sync = temp_db.query(SyncLog).order_by(SyncLog.synced_at.desc()).first()
    pending = temp_db.query(Demand).filter(Demand.status == RequestStatus.PENDING).order_by(Demand.created_at.desc()).limit(6).all()
    return templates.TemplateResponse("pmo/dashboard.html", {"request": request, "user": user, "metrics": metrics, "latest_sync": latest_sync, "pending": pending})


@router.post("/sync")
def sync_databases(user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    SyncService.synchronize(main_db, temp_db, user.username)
    return RedirectResponse("/pmo/dashboard?message=sync-complete", status_code=303)


@router.get("/resources", response_class=HTMLResponse)
def resources(request: Request, search: str | None = None, user: User = Depends(require_role(UserRole.PMO)), db: Session = Depends(get_temp_db)):
    query = db.query(Resource).filter(Resource.is_active.is_(True))
    if search:
        like = f"%{search}%"
        query = query.filter((Resource.name.ilike(like)) | (Resource.role.ilike(like)) | (Resource.skill.ilike(like)) | (Resource.employee_id.ilike(like)))
    message = request.query_params.get("message")
    error = request.query_params.get("error")
    resources = query.order_by(Resource.skill, Resource.name).all()
    return templates.TemplateResponse("pmo/resources.html", {"request": request, "user": user, "resources": resources, "search": search or "", "message": message, "error": error})


@router.post("/resources/add")
def add_resource(
    employee_id: str = Form(...),
    name: str = Form(...),
    skill: str = Form(...),
    role: str = Form(...),
    level: int = Form(...),
    location: str = Form(...),
    current_allocation: int = Form(0),
    available_from: date = Form(...),
    cv_file: UploadFile | None = File(None),
    employee_username: str = Form(...),
    employee_email: str = Form(...),
    employee_password: str = Form(...),
    user: User = Depends(require_role(UserRole.PMO)),
    main_db: Session = Depends(get_main_db),
    temp_db: Session = Depends(get_temp_db),
):
    existing = main_db.query(Resource).filter(Resource.employee_id == employee_id.strip()).first()
    if existing:
        return RedirectResponse("/pmo/resources?error=employee-exists", status_code=303)
    if main_db.query(User).filter((User.username == employee_username.strip()) | (User.email == employee_email.strip())).first():
        return RedirectResponse("/pmo/resources?error=login-exists", status_code=303)

    employee_user = User(username=employee_username.strip(), full_name=name.strip(), email=employee_email.strip(), role=UserRole.EMPLOYEE, password_hash=hash_password(employee_password))
    main_db.add(employee_user)
    main_db.flush()

    data = {
        "employee_id": employee_id.strip(),
        "name": name.strip(),
        "skill": skill.strip(),
        "role": role.strip(),
        "level": max(1, min(level, 5)),
        "location": location.strip(),
        "current_allocation": max(0, min(current_allocation, 100)),
        "reserved_allocation": 0,
        "available_from": available_from,
        "is_active": True,
        "user_id": employee_user.id,
    }
    main_resource = Resource(**data)
    main_db.add(main_resource)
    main_db.commit()
    main_db.refresh(main_resource)

    if cv_file and cv_file.filename:
        try:
            cv_path = save_cv(main_resource.id, cv_file)
        except ValueError:
            main_db.delete(main_resource)
            main_db.delete(employee_user)
            main_db.commit()
            return RedirectResponse("/pmo/resources?error=invalid-cv", status_code=303)
        main_resource.cv_path = cv_path
        main_db.commit()
        data["cv_path"] = cv_path

    temp_db.add(User(id=employee_user.id, username=employee_user.username, full_name=employee_user.full_name, email=employee_user.email, role=employee_user.role, password_hash=employee_user.password_hash, is_active=True, created_at=employee_user.created_at))
    temp_db.add(Resource(id=main_resource.id, **data))
    temp_db.commit()
    return RedirectResponse("/pmo/resources?message=resource-added", status_code=303)


@router.post("/resources/{resource_id}/cv")
def upload_cv(resource_id: int, cv_file: UploadFile = File(...), user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    main_resource = main_db.get(Resource, resource_id)
    temp_resource = temp_db.get(Resource, resource_id)
    if not main_resource or not temp_resource:
        return RedirectResponse("/pmo/resources?error=resource-not-found", status_code=303)
    try:
        cv_path = save_cv(resource_id, cv_file)
    except ValueError:
        return RedirectResponse("/pmo/resources?error=invalid-cv", status_code=303)
    for resource in (main_resource, temp_resource):
        resource.cv_path = cv_path
        resource.cv_requested = False
        resource.cv_request_message = None
        resource.cv_requested_at = None
    main_db.commit()
    temp_db.commit()
    return RedirectResponse("/pmo/resources?message=cv-updated", status_code=303)


@router.post("/resources/{resource_id}/request-cv")
def request_cv(resource_id: int, message: str | None = Form(None), user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    main_resource = main_db.get(Resource, resource_id)
    temp_resource = temp_db.get(Resource, resource_id)
    if not main_resource:
        return RedirectResponse("/pmo/resources?error=resource-not-found", status_code=303)
    for resource in (main_resource, temp_resource):
        if resource:
            resource.cv_requested = True
            resource.cv_request_message = message or "Please upload or update your CV."
            resource.cv_requested_at = datetime.utcnow()
    main_db.commit()
    temp_db.commit()
    return RedirectResponse("/pmo/resources?message=cv-requested", status_code=303)


@router.post("/resources/{resource_id}/remove")
def remove_resource(resource_id: int, user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    main_resource = main_db.get(Resource, resource_id)
    temp_resource = temp_db.get(Resource, resource_id)
    if not main_resource and not temp_resource:
        return RedirectResponse("/pmo/resources?error=resource-not-found", status_code=303)
    if temp_resource and (temp_resource.current_allocation > 0 or temp_resource.reserved_allocation > 0):
        return RedirectResponse("/pmo/resources?error=resource-allocated", status_code=303)

    if main_resource:
        main_resource.is_active = False
    if temp_resource:
        temp_resource.is_active = False
    main_db.commit()
    temp_db.commit()
    return RedirectResponse("/pmo/resources?message=resource-removed", status_code=303)


@router.get("/projects", response_class=HTMLResponse)
def projects(request: Request, user: User = Depends(require_role(UserRole.PMO)), db: Session = Depends(get_temp_db)):
    return templates.TemplateResponse("pmo/projects.html", {"request": request, "user": user, "projects": db.query(Project).order_by(Project.name).all()})


@router.get("/requests", response_class=HTMLResponse)
def requests_page(request: Request, status: str | None = None, user: User = Depends(require_role(UserRole.PMO)), db: Session = Depends(get_temp_db)):
    query = db.query(Demand)
    if status:
        query = query.filter(Demand.status == RequestStatus(status))
    demands = query.order_by(Demand.created_at.desc()).all()
    return templates.TemplateResponse("pmo/requests.html", {"request": request, "user": user, "demands": demands, "status": status or ""})


@router.get("/block-requests", response_class=HTMLResponse)
def block_requests(request: Request, status: str | None = None, user: User = Depends(require_role(UserRole.PMO)), db: Session = Depends(get_temp_db)):
    query = db.query(ResourceBlock)
    if status:
        query = query.filter(ResourceBlock.status == BlockStatus(status))
    blocks = query.order_by(ResourceBlock.created_at.desc()).all()
    return templates.TemplateResponse("pmo/block_requests.html", {"request": request, "user": user, "blocks": blocks, "status": status or "", "error": request.query_params.get("error")})


@router.post("/block-requests/{block_id}/approve")
def approve_block(block_id: int, remarks: str | None = Form(None), user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    try:
        ResourceBlockService(main_db, temp_db).decide(block_id, user, True, remarks)
    except ValueError as exc:
        return RedirectResponse(f"/pmo/block-requests?error={quote(str(exc))}", status_code=303)
    return RedirectResponse("/pmo/block-requests?status=PENDING", status_code=303)


@router.post("/block-requests/{block_id}/reject")
def reject_block(block_id: int, remarks: str | None = Form(None), user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    ResourceBlockService(main_db, temp_db).decide(block_id, user, False, remarks)
    return RedirectResponse("/pmo/block-requests?status=PENDING", status_code=303)


@router.post("/requests/{demand_id}/approve")
def approve_request(demand_id: int, remarks: str | None = Form(None), user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    ApprovalService(main_db, temp_db).approve(demand_id, user, remarks)
    return RedirectResponse("/pmo/requests?status=PENDING", status_code=303)


@router.post("/requests/{demand_id}/reject")
def reject_request(demand_id: int, remarks: str | None = Form(None), user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    ApprovalService(main_db, temp_db).reject(demand_id, user, remarks)
    return RedirectResponse("/pmo/requests?status=PENDING", status_code=303)


@router.post("/requests/{demand_id}/modify")
def modify_request(demand_id: int, allocation_percent: int = Form(...), remarks: str | None = Form(None), user: User = Depends(require_role(UserRole.PMO)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    ApprovalService(main_db, temp_db).modify(demand_id, allocation_percent, remarks)
    return RedirectResponse("/pmo/requests?status=PENDING", status_code=303)


@router.get("/reports", response_class=HTMLResponse)
def reports(request: Request, user: User = Depends(require_role(UserRole.PMO)), db: Session = Depends(get_temp_db)):
    service = ReportService(db)
    context = {
        "request": request,
        "user": user,
        "metrics": service.dashboard_metrics(),
        "utilization": service.resource_utilization(),
        "skills": service.skill_availability(),
        "projects": service.allocation_by_project(),
        "demands": db.query(Demand).order_by(Demand.created_at.desc()).all(),
    }
    return templates.TemplateResponse("pmo/reports.html", context)


@router.get("/audit-logs", response_class=HTMLResponse)
def audit_logs(request: Request, user: User = Depends(require_role(UserRole.PMO)), db: Session = Depends(get_main_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return templates.TemplateResponse("pmo/audit_logs.html", {"request": request, "user": user, "logs": logs})
