from datetime import date, timedelta

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import MainSessionLocal, TempSessionLocal, main_engine, temp_engine
from app.models import Allocation, ExtensionStatus, Project, ProjectStatus, Resource, User, UserRole
from app.services.sync_service import SyncService


def create_all() -> None:
    Base.metadata.create_all(bind=main_engine)
    Base.metadata.create_all(bind=temp_engine)
    migrate_schema()


def migrate_schema() -> None:
    for engine in (main_engine, temp_engine):
        inspector = inspect(engine)
        if not inspector.has_table("allocations"):
            continue
        columns = {column["name"] for column in inspector.get_columns("allocations")}
        with engine.begin() as connection:
            if "extension_status" not in columns:
                connection.execute(text("ALTER TABLE allocations ADD COLUMN extension_status VARCHAR(30) DEFAULT 'NOT_DUE'"))
            if "extension_remarks" not in columns:
                connection.execute(text("ALTER TABLE allocations ADD COLUMN extension_remarks TEXT"))
        resource_columns = {column["name"] for column in inspector.get_columns("resources")}
        if "cv_path" not in resource_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE resources ADD COLUMN cv_path VARCHAR(255)"))
        if "role" not in resource_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE resources ADD COLUMN role VARCHAR(80) DEFAULT 'Developer'"))
        resource_migrations = {
            "user_id": "INTEGER REFERENCES users(id)",
            "phone": "VARCHAR(30)",
            "years_experience": "INTEGER DEFAULT 0",
            "additional_skills": "TEXT",
            "bio": "TEXT",
            "current_status": "VARCHAR(40) DEFAULT 'Available'",
            "education": "TEXT",
            "certifications": "TEXT",
            "cv_requested": "BOOLEAN DEFAULT 0",
            "cv_request_message": "TEXT",
            "cv_requested_at": "DATETIME",
        }
        for column_name, definition in resource_migrations.items():
            if column_name not in resource_columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE resources ADD COLUMN {column_name} {definition}"))
        if inspector.has_table("demands"):
            demand_columns = {column["name"] for column in inspector.get_columns("demands")}
            if "required_role" not in demand_columns:
                with engine.begin() as connection:
                    connection.execute(text("ALTER TABLE demands ADD COLUMN required_role VARCHAR(80) DEFAULT 'Developer'"))


def seed_main_database() -> None:
    db = MainSessionLocal()
    try:
        if db.query(User).first():
            employee = db.query(User).filter(User.username == "employee1").first()
            if not employee:
                employee = User(username="employee1", full_name="Nisha Patel", email="nisha.patel@example.com", role=UserRole.EMPLOYEE, password_hash=hash_password("employee123"))
                db.add(employee)
                db.flush()
            for index, resource in enumerate(db.query(Resource).order_by(Resource.id).all(), start=1):
                username = f"employee{index}"
                employee_user = db.query(User).filter(User.username == username).first()
                if not employee_user:
                    employee_user = User(username=username, full_name=resource.name, email=f"{resource.employee_id.lower()}@example.com", role=UserRole.EMPLOYEE, password_hash=hash_password("employee123"))
                    db.add(employee_user)
                    db.flush()
                resource.user_id = resource.user_id or employee_user.id
                resource.current_status = resource.current_status or ("Allocated" if resource.current_allocation else "Available")
            resource = db.query(Resource).filter(Resource.employee_id == "E1001").first()
            if resource:
                resource.phone = resource.phone or "+91 90000 10001"
                resource.years_experience = resource.years_experience or 7
                resource.additional_skills = resource.additional_skills or "FastAPI, SQLAlchemy, PostgreSQL, Docker"
            db.commit()
            return

        pmo = User(
            username="pmo",
            full_name="Priya Menon",
            email="pmo@example.com",
            role=UserRole.PMO,
            password_hash=hash_password("pmo123"),
        )
        lead1 = User(
            username="lead1",
            full_name="Aarav Sharma",
            email="lead1@example.com",
            role=UserRole.PROJECT_LEAD,
            password_hash=hash_password("lead123"),
        )
        lead2 = User(
            username="lead2",
            full_name="Maya Rao",
            email="lead2@example.com",
            role=UserRole.PROJECT_LEAD,
            password_hash=hash_password("lead123"),
        )
        employee = User(
            username="employee1",
            full_name="Nisha Patel",
            email="nisha.patel@example.com",
            role=UserRole.EMPLOYEE,
            password_hash=hash_password("employee123"),
        )
        db.add_all([pmo, lead1, lead2, employee])
        db.flush()

        today = date.today()
        projects = [
            Project(name="Payments Modernization", code="PAY-101", description="Core payment rails upgrade.", lead_id=lead1.id, status=ProjectStatus.ACTIVE, start_date=today - timedelta(days=90), end_date=today + timedelta(days=210)),
            Project(name="Customer 360", code="C360", description="Unified customer data platform.", lead_id=lead1.id, status=ProjectStatus.ACTIVE, start_date=today - timedelta(days=45), end_date=today + timedelta(days=180)),
            Project(name="Risk Analytics", code="RISK", description="Portfolio risk analytics and dashboards.", lead_id=lead2.id, status=ProjectStatus.ACTIVE, start_date=today - timedelta(days=30), end_date=today + timedelta(days=150)),
            Project(name="Mobile App Refresh", code="MOB", description="Experience refresh for mobile channels.", lead_id=lead2.id, status=ProjectStatus.ON_HOLD, start_date=today - timedelta(days=120), end_date=today + timedelta(days=20)),
        ]
        db.add_all(projects)
        db.flush()

        resources = [
            Resource(user_id=employee.id, employee_id="E1001", name="Nisha Patel", role="Backend Developer", skill="Python", level=4, location="Bengaluru", current_allocation=50, available_from=today, phone="+91 90000 10001", years_experience=7, additional_skills="FastAPI, SQLAlchemy, PostgreSQL, Docker", current_status="Allocated", education="B.Tech in Computer Science", certifications="AWS Certified Developer"),
            Resource(employee_id="E1002", name="Rohan Verma", role="Backend Developer", skill="Python", level=3, location="Pune", current_allocation=0, available_from=today),
            Resource(employee_id="E1003", name="Isha Nair", role="Data Engineer", skill="Data Engineering", level=5, location="Hyderabad", current_allocation=75, available_from=today + timedelta(days=15)),
            Resource(employee_id="E1004", name="Kabir Singh", role="Frontend Developer", skill="React", level=4, location="Mumbai", current_allocation=25, available_from=today),
            Resource(employee_id="E1005", name="Anika Bose", role="QA Engineer", skill="QA Automation", level=3, location="Kolkata", current_allocation=0, available_from=today),
            Resource(employee_id="E1006", name="Dev Mehta", role="Technical Lead", skill="Python", level=5, location="Remote", current_allocation=90, available_from=today + timedelta(days=30)),
            Resource(employee_id="E1007", name="Sara Khan", role="Business Analyst", skill="Business Analysis", level=4, location="Delhi", current_allocation=60, available_from=today),
            Resource(employee_id="E1008", name="Vikram Iyer", role="Data Engineer", skill="Data Engineering", level=3, location="Chennai", current_allocation=0, available_from=today),
            Resource(employee_id="E1009", name="Meera Joshi", role="Frontend Developer", skill="React", level=2, location="Bengaluru", current_allocation=0, available_from=today),
            Resource(employee_id="E1010", name="Aditya Kulkarni", role="Cloud Engineer", skill="Cloud", level=4, location="Pune", current_allocation=40, available_from=today),
        ]
        db.add_all(resources)
        db.flush()

        for index, resource in enumerate(resources[1:], start=2):
            employee_user = User(username=f"employee{index}", full_name=resource.name, email=f"{resource.employee_id.lower()}@example.com", role=UserRole.EMPLOYEE, password_hash=hash_password("employee123"))
            db.add(employee_user)
            db.flush()
            resource.user_id = employee_user.id

        allocations = [
            Allocation(resource_id=resources[0].id, project_id=projects[0].id, allocation_percent=50, start_date=today - timedelta(days=30), end_date=today + timedelta(days=120)),
            Allocation(resource_id=resources[2].id, project_id=projects[2].id, allocation_percent=75, start_date=today - timedelta(days=20), end_date=today + timedelta(days=110)),
            Allocation(resource_id=resources[3].id, project_id=projects[1].id, allocation_percent=25, start_date=today - timedelta(days=10), end_date=today + timedelta(days=90)),
            Allocation(resource_id=resources[6].id, project_id=projects[3].id, allocation_percent=60, start_date=today - timedelta(days=50), end_date=today + timedelta(days=20), extension_status=ExtensionStatus.YET_TO_BE_UPDATED),
            Allocation(resource_id=resources[9].id, project_id=projects[0].id, allocation_percent=40, start_date=today - timedelta(days=15), end_date=today + timedelta(days=130)),
        ]
        db.add_all(allocations)
        db.commit()
    finally:
        db.close()


def initialize_databases() -> None:
    create_all()
    seed_main_database()
    with MainSessionLocal() as main_db, TempSessionLocal() as temp_db:
        if not temp_db.query(User).first():
            SyncService.synchronize(main_db, temp_db, "system")
        else:
            for employee in main_db.query(User).filter(User.role == UserRole.EMPLOYEE).all():
                if not temp_db.get(User, employee.id):
                    data = {column.name: getattr(employee, column.name) for column in User.__table__.columns}
                    temp_db.merge(User(**data))
            for main_resource in main_db.query(Resource).all():
                temp_resource = temp_db.get(Resource, main_resource.id)
                if temp_resource:
                    for field in ("user_id", "phone", "years_experience", "additional_skills", "bio", "current_status", "education", "certifications", "cv_path", "cv_requested", "cv_request_message", "cv_requested_at"):
                        setattr(temp_resource, field, getattr(main_resource, field))
            temp_db.commit()
    update_due_extension_statuses()


def update_due_extension_statuses() -> None:
    today = date.today()
    due_date = today + timedelta(days=30)
    for session_factory in (MainSessionLocal, TempSessionLocal):
        with session_factory() as db:
            allocations = (
                db.query(Allocation)
                .join(Project, Allocation.project_id == Project.id)
                .filter(Project.end_date.is_not(None), Project.end_date <= due_date, Project.end_date >= today)
                .all()
            )
            for allocation in allocations:
                if allocation.extension_status == ExtensionStatus.NOT_DUE:
                    allocation.extension_status = ExtensionStatus.YET_TO_BE_UPDATED
            db.commit()


def reset_and_seed() -> None:
    Base.metadata.drop_all(bind=main_engine)
    Base.metadata.drop_all(bind=temp_engine)
    initialize_databases()
