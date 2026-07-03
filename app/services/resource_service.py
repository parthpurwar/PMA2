from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import BlockStatus, Demand, Recommendation, RequestStatus, Resource, ResourceBlock


class ResourceMatchingService:
    def __init__(self, db: Session):
        self.db = db

    def create_demand(self, **data) -> Demand:
        demand = Demand(**data, status=RequestStatus.DRAFT)
        self.db.add(demand)
        self.db.commit()
        self.db.refresh(demand)
        self.generate_recommendations(demand)
        return demand

    def generate_recommendations(self, demand: Demand) -> list[Recommendation]:
        self.db.query(Recommendation).filter(Recommendation.demand_id == demand.id).delete()
        candidates = self.db.query(Resource).filter(Resource.is_active.is_(True)).all()
        ranked = sorted(((self._score(demand, resource), resource.id, resource) for resource in candidates), key=lambda item: (item[0][0], item[0][1], item[1]))
        recommendations: list[Recommendation] = []
        for rank, ((bucket, score, reason), _resource_id, resource) in enumerate(ranked[:12], start=1):
            recommendation = Recommendation(
                demand_id=demand.id,
                resource_id=resource.id,
                rank=rank,
                score=score,
                reason=reason,
            )
            self.db.add(recommendation)
            recommendations.append(recommendation)
        self.db.commit()
        return recommendations

    def reserve_resources(self, demand_id: int, resource_ids: list[int]) -> Demand:
        demand = self.db.get(Demand, demand_id)
        if not demand:
            raise ValueError("Demand not found.")
        selected = self.db.query(Recommendation).filter(
            Recommendation.demand_id == demand.id,
            Recommendation.resource_id.in_(resource_ids),
        ).all()
        for recommendation in selected:
            conflict = self.db.query(ResourceBlock).filter(
                ResourceBlock.resource_id == recommendation.resource_id,
                ResourceBlock.status.in_([BlockStatus.PENDING, BlockStatus.APPROVED]),
                ResourceBlock.start_date <= demand.end_date,
                ResourceBlock.end_date >= demand.start_date,
            ).first()
            if conflict:
                raise ValueError(f"{recommendation.resource.name} is blocked or awaiting block approval for these dates.")
        for recommendation in demand.recommendations:
            recommendation.is_selected = recommendation.resource_id in resource_ids
        for recommendation in selected:
            resource = recommendation.resource
            resource.reserved_allocation = min(100, resource.reserved_allocation + demand.allocation_percent)
        demand.status = RequestStatus.PENDING
        self.db.commit()
        return demand

    def release_reserved_resources(self, demand: Demand) -> None:
        for recommendation in demand.recommendations:
            if recommendation.is_selected:
                recommendation.resource.reserved_allocation = max(0, recommendation.resource.reserved_allocation - demand.allocation_percent)
                recommendation.is_selected = False
        self.db.commit()

    def _score(self, demand: Demand, resource: Resource) -> tuple[int, int, str]:
        block_conflict = self.db.query(ResourceBlock).filter(
            ResourceBlock.resource_id == resource.id,
            ResourceBlock.status.in_([BlockStatus.PENDING, BlockStatus.APPROVED]),
            ResourceBlock.start_date <= demand.end_date,
            ResourceBlock.end_date >= demand.start_date,
        ).first()
        if block_conflict:
            return (6, 9999, "Unavailable: blocked or awaiting block approval for these dates")
        available_capacity = max(0, 100 - resource.current_allocation - resource.reserved_allocation)
        skill_match = resource.skill.lower() == demand.required_skill.lower()
        role_match = resource.role.lower() == demand.required_role.lower()
        fully_available = available_capacity >= demand.allocation_percent and resource.available_from <= demand.start_date
        if role_match and skill_match and resource.level == demand.required_level and fully_available:
            return (1, 100 - available_capacity, "Exact role, skill, and level with enough capacity")
        if role_match and skill_match and resource.level > demand.required_level:
            return (2, (resource.level - demand.required_level) * 10 + resource.current_allocation, "Exact role and skill with higher level")
        if role_match and skill_match and resource.level < demand.required_level:
            return (3, (demand.required_level - resource.level) * 10 + resource.current_allocation, "Exact role and skill with lower level")
        if skill_match:
            return (4, resource.current_allocation + resource.reserved_allocation, "Skill match; role differs")
        days_until_available = abs((resource.available_from - date.today()).days)
        return (5, days_until_available + abs(resource.level - demand.required_level) * 20, "Nearest available resource by role, level, and date")


def searchable_resources(db: Session, search: str | None = None, skill: str | None = None):
    query = db.query(Resource).filter(Resource.is_active.is_(True))
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Resource.name.ilike(like), Resource.employee_id.ilike(like), Resource.role.ilike(like), Resource.skill.ilike(like)))
    if skill:
        query = query.filter(Resource.skill == skill)
    return query.order_by(Resource.skill, Resource.level.desc(), Resource.current_allocation)
