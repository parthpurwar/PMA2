from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Allocation, ApprovalHistory, AuditLog, Demand, ExtensionStatus, Recommendation, RequestStatus, Resource, User
from app.services.resource_service import ResourceMatchingService


class ApprovalService:
    def __init__(self, main_db: Session, temp_db: Session):
        self.main_db = main_db
        self.temp_db = temp_db

    def approve(self, demand_id: int, pmo: User, remarks: str | None = None) -> Demand:
        temp_demand = self.temp_db.get(Demand, demand_id)
        if not temp_demand:
            raise ValueError("Demand not found.")
        selected = [r for r in temp_demand.recommendations if r.is_selected]
        if not selected:
            raise ValueError("No selected resources to approve.")

        main_demand = self.main_db.get(Demand, demand_id)
        if not main_demand:
            main_demand = self._clone_demand(temp_demand, RequestStatus.APPROVED)
            self.main_db.add(main_demand)
        else:
            main_demand.status = RequestStatus.APPROVED
            main_demand.remarks = temp_demand.remarks

        old_allocations: list[str] = []
        new_allocations: list[str] = []
        resource_names: list[str] = []

        for temp_recommendation in selected:
            temp_resource = temp_recommendation.resource
            main_resource = self.main_db.get(Resource, temp_resource.id)
            if not main_resource:
                continue
            old_allocations.append(f"{main_resource.name}: {main_resource.current_allocation}%")
            main_resource.current_allocation = min(100, main_resource.current_allocation + temp_demand.allocation_percent)
            main_resource.reserved_allocation = 0
            new_allocations.append(f"{main_resource.name}: {main_resource.current_allocation}%")
            resource_names.append(main_resource.name)
            self.main_db.add(Allocation(
                resource_id=main_resource.id,
                project_id=temp_demand.project_id,
                allocation_percent=temp_demand.allocation_percent,
                start_date=temp_demand.start_date,
                end_date=temp_demand.end_date,
                status="Active",
                extension_status=self._extension_status_for_project(temp_demand),
                demand_id=temp_demand.id,
            ))

        temp_demand.status = RequestStatus.APPROVED
        for recommendation in selected:
            recommendation.resource.current_allocation = min(100, recommendation.resource.current_allocation + temp_demand.allocation_percent)
            recommendation.resource.reserved_allocation = max(0, recommendation.resource.reserved_allocation - temp_demand.allocation_percent)

        approval = ApprovalHistory(demand_id=temp_demand.id, action=RequestStatus.APPROVED, pmo_id=pmo.id, remarks=remarks)
        main_approval = ApprovalHistory(demand_id=temp_demand.id, action=RequestStatus.APPROVED, pmo_id=pmo.id, remarks=remarks)
        audit = AuditLog(
            pmo_username=pmo.username,
            project_lead_username=temp_demand.requested_by.username,
            demand_id=temp_demand.id,
            old_allocation="; ".join(old_allocations),
            new_allocation="; ".join(new_allocations),
            resources_updated=", ".join(resource_names),
            remarks=remarks,
        )
        self.temp_db.add(approval)
        self.main_db.add(main_approval)
        self.main_db.add(audit)
        self.temp_db.commit()
        self.main_db.commit()
        return temp_demand

    def reject(self, demand_id: int, pmo: User, remarks: str | None = None) -> Demand:
        demand = self.temp_db.get(Demand, demand_id)
        if not demand:
            raise ValueError("Demand not found.")
        ResourceMatchingService(self.temp_db).release_reserved_resources(demand)
        demand.status = RequestStatus.REJECTED
        self.temp_db.add(ApprovalHistory(demand_id=demand.id, action=RequestStatus.REJECTED, pmo_id=pmo.id, remarks=remarks))
        self.temp_db.commit()
        return demand

    def modify(self, demand_id: int, allocation_percent: int, remarks: str | None) -> Demand:
        demand = self.temp_db.get(Demand, demand_id)
        if not demand:
            raise ValueError("Demand not found.")
        delta = allocation_percent - demand.allocation_percent
        for recommendation in demand.recommendations:
            if recommendation.is_selected:
                recommendation.resource.reserved_allocation = max(0, min(100, recommendation.resource.reserved_allocation + delta))
        demand.allocation_percent = allocation_percent
        demand.remarks = remarks or demand.remarks
        demand.status = RequestStatus.PENDING
        self.temp_db.commit()
        return demand

    def _clone_demand(self, demand: Demand, status: RequestStatus) -> Demand:
        return Demand(
            id=demand.id,
            project_id=demand.project_id,
            requested_by_id=demand.requested_by_id,
            required_skill=demand.required_skill,
            required_role=demand.required_role,
            required_level=demand.required_level,
            number_of_resources=demand.number_of_resources,
            allocation_percent=demand.allocation_percent,
            start_date=demand.start_date,
            end_date=demand.end_date,
            priority=demand.priority,
            remarks=demand.remarks,
            status=status,
            created_at=demand.created_at,
            updated_at=demand.updated_at,
        )

    def _extension_status_for_project(self, demand: Demand) -> ExtensionStatus:
        if demand.project.end_date and date.today() <= demand.project.end_date <= date.today() + timedelta(days=30):
            return ExtensionStatus.YET_TO_BE_UPDATED
        return ExtensionStatus.NOT_DUE
