from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Allocation, Demand, Project, RequestStatus, Resource


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def dashboard_metrics(self) -> dict[str, int]:
        return {
            "resources": self.db.query(Resource).count(),
            "available": self.db.query(Resource).filter(Resource.current_allocation < 100).count(),
            "bench": self.db.query(Resource).filter(Resource.current_allocation == 0).count(),
            "projects": self.db.query(Project).count(),
            "pending": self.db.query(Demand).filter(Demand.status == RequestStatus.PENDING).count(),
            "approved": self.db.query(Demand).filter(Demand.status == RequestStatus.APPROVED).count(),
        }

    def resource_utilization(self) -> list[dict[str, str | int]]:
        resources = self.db.query(Resource).order_by(Resource.current_allocation.desc()).all()
        return [{"name": r.name, "skill": r.skill, "allocation": r.current_allocation, "bench": max(0, 100 - r.current_allocation)} for r in resources]

    def skill_availability(self) -> list[dict[str, str | int]]:
        rows = self.db.query(Resource.skill, func.count(Resource.id), func.sum(100 - Resource.current_allocation)).group_by(Resource.skill).all()
        return [{"skill": skill, "count": count, "capacity": int(capacity or 0)} for skill, count, capacity in rows]

    def allocation_by_project(self) -> list[dict[str, str | int]]:
        rows = (
            self.db.query(Project.name, func.count(Allocation.id), func.coalesce(func.sum(Allocation.allocation_percent), 0))
            .outerjoin(Allocation, Allocation.project_id == Project.id)
            .group_by(Project.id)
            .all()
        )
        return [{"project": name, "resources": count, "allocation": int(total)} for name, count, total in rows]
