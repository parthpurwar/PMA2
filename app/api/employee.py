from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_main_db, get_temp_db
from app.models import Resource, User, UserRole
from app.services.cv_service import save_cv

router = APIRouter(prefix="/employee")
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(require_role(UserRole.EMPLOYEE)), db: Session = Depends(get_main_db)):
    resource = db.query(Resource).filter(Resource.user_id == user.id).first()
    return templates.TemplateResponse("employee/dashboard.html", {"request": request, "user": user, "resource": resource, "message": request.query_params.get("message"), "error": request.query_params.get("error")})


@router.post("/profile")
def update_profile(
    phone: str | None = Form(None),
    location: str = Form(...),
    additional_skills: str | None = Form(None),
    years_experience: int = Form(0),
    current_status: str = Form(...),
    education: str | None = Form(None),
    certifications: str | None = Form(None),
    bio: str | None = Form(None),
    user: User = Depends(require_role(UserRole.EMPLOYEE)),
    main_db: Session = Depends(get_main_db),
    temp_db: Session = Depends(get_temp_db),
):
    main_resource = main_db.query(Resource).filter(Resource.user_id == user.id).first()
    if not main_resource:
        return RedirectResponse("/employee/dashboard?error=profile-not-linked", status_code=303)
    values = {"phone": phone, "location": location.strip(), "additional_skills": additional_skills, "years_experience": max(0, years_experience), "current_status": current_status, "education": education, "certifications": certifications, "bio": bio}
    for key, value in values.items():
        setattr(main_resource, key, value)
    temp_resource = temp_db.get(Resource, main_resource.id)
    if temp_resource:
        for key, value in values.items():
            setattr(temp_resource, key, value)
    main_db.commit()
    temp_db.commit()
    return RedirectResponse("/employee/dashboard?message=profile-updated", status_code=303)


@router.post("/cv")
def upload_cv(cv_file: UploadFile = File(...), user: User = Depends(require_role(UserRole.EMPLOYEE)), main_db: Session = Depends(get_main_db), temp_db: Session = Depends(get_temp_db)):
    main_resource = main_db.query(Resource).filter(Resource.user_id == user.id).first()
    if not main_resource:
        return RedirectResponse("/employee/dashboard?error=profile-not-linked", status_code=303)
    try:
        cv_path = save_cv(main_resource.id, cv_file)
    except ValueError:
        return RedirectResponse("/employee/dashboard?error=invalid-cv", status_code=303)
    main_resource.cv_path = cv_path
    main_resource.cv_requested = False
    main_resource.cv_request_message = None
    main_resource.cv_requested_at = None
    temp_resource = temp_db.get(Resource, main_resource.id)
    if temp_resource:
        temp_resource.cv_path = cv_path
        temp_resource.cv_requested = False
        temp_resource.cv_request_message = None
        temp_resource.cv_requested_at = None
    main_db.commit()
    temp_db.commit()
    return RedirectResponse("/employee/dashboard?message=cv-uploaded", status_code=303)
