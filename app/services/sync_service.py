from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import temp_engine
from app.models import Allocation, ApprovalHistory, AuditLog, Demand, ExtensionStatus, Project, Recommendation, Resource, ResourceBlock, SyncLog, User


class SyncService:
    COPY_MODELS = [User, Project, Resource, Demand, Recommendation, Allocation, ApprovalHistory, AuditLog, ResourceBlock]

    @classmethod
    def synchronize(cls, main_db: Session, temp_db: Session, username: str) -> SyncLog:
        Base.metadata.drop_all(bind=temp_engine)
        Base.metadata.create_all(bind=temp_engine)
        for model in cls.COPY_MODELS:
            for row in main_db.query(model).all():
                data = {column.name: getattr(row, column.name) for column in model.__table__.columns}
                temp_db.merge(model(**data))
        log = SyncLog(synced_by=username, status="SUCCESS", details="Temporary database refreshed from production.")
        temp_db.add(log)
        cls.mark_due_extensions(temp_db)
        temp_db.commit()
        return log

    @classmethod
    def mark_due_extensions(cls, temp_db: Session) -> None:
        today = date.today()
        due_date = today + timedelta(days=30)
        allocations = (
            temp_db.query(Allocation)
            .join(Project, Allocation.project_id == Project.id)
            .filter(Project.end_date.is_not(None), Project.end_date >= today, Project.end_date <= due_date)
            .all()
        )
        for allocation in allocations:
            if allocation.extension_status == ExtensionStatus.NOT_DUE:
                allocation.extension_status = ExtensionStatus.YET_TO_BE_UPDATED
