import calendar
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import Allocation, BlockStatus, Resource, ResourceBlock, User


class ResourceBlockService:
    def __init__(self, main_db: Session | None, temp_db: Session):
        self.main_db = main_db
        self.temp_db = temp_db

    def is_free(self, resource_id: int, start_date: date, end_date: date, exclude_block_id: int | None = None) -> bool:
        if end_date < start_date:
            return False
        allocation = self.temp_db.query(Allocation).filter(
            Allocation.resource_id == resource_id,
            Allocation.status == "Active",
            Allocation.start_date <= end_date,
            Allocation.end_date >= start_date,
        ).first()
        query = self.temp_db.query(ResourceBlock).filter(
            ResourceBlock.resource_id == resource_id,
            ResourceBlock.status.in_([BlockStatus.PENDING, BlockStatus.APPROVED]),
            ResourceBlock.start_date <= end_date,
            ResourceBlock.end_date >= start_date,
        )
        if exclude_block_id:
            query = query.filter(ResourceBlock.id != exclude_block_id)
        return allocation is None and query.first() is None

    def request(self, resource_id: int, lead: User, start_date: date, end_date: date, project_id: int | None, reason: str | None) -> ResourceBlock:
        resource = self.temp_db.get(Resource, resource_id)
        if not resource or not resource.is_active:
            raise ValueError("Resource not found.")
        if start_date < date.today() or end_date < start_date:
            raise ValueError("Choose a valid current or future date range.")
        if project_id and not any(project.id == project_id for project in lead.projects):
            raise ValueError("You can only block a resource for one of your projects.")
        if not self.is_free(resource_id, start_date, end_date):
            raise ValueError("The resource is already allocated, blocked, or awaiting approval in that period.")
        block = ResourceBlock(
            resource_id=resource_id,
            requested_by_id=lead.id,
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status=BlockStatus.PENDING,
        )
        self.temp_db.add(block)
        self.temp_db.commit()
        self.temp_db.refresh(block)
        return block

    def decide(self, block_id: int, pmo: User, approve: bool, remarks: str | None) -> ResourceBlock:
        block = self.temp_db.get(ResourceBlock, block_id)
        if not block or block.status != BlockStatus.PENDING:
            raise ValueError("Pending block request not found.")
        if approve and not self.is_free(block.resource_id, block.start_date, block.end_date, block.id):
            raise ValueError("The resource is no longer free for this period.")
        block.status = BlockStatus.APPROVED if approve else BlockStatus.REJECTED
        block.pmo_id = pmo.id
        block.pmo_remarks = remarks
        block.decided_at = datetime.utcnow()
        if approve and self.main_db:
            data = {column.name: getattr(block, column.name) for column in ResourceBlock.__table__.columns}
            self.main_db.merge(ResourceBlock(**data))
            self.main_db.commit()
        self.temp_db.commit()
        return block


def booking_calendars(resources: list[Resource], months: int = 3) -> dict[int, list[dict]]:
    """Build full month grids for the block dialog; unavailable dates are shown in red."""
    today = date.today()
    result: dict[int, list[dict]] = {}
    month_builder = calendar.Calendar(firstweekday=0)
    for resource in resources:
        resource_months: list[dict] = []
        for offset in range(months):
            month_index = today.month - 1 + offset
            year = today.year + month_index // 12
            month = month_index % 12 + 1
            weeks = []
            for week in month_builder.monthdatescalendar(year, month):
                cells = []
                for day in week:
                    unavailable = any(
                        allocation.status == "Active" and allocation.start_date <= day <= allocation.end_date
                        for allocation in resource.allocations
                    ) or any(
                        block.status in (BlockStatus.PENDING, BlockStatus.APPROVED) and block.start_date <= day <= block.end_date
                        for block in resource.blocks
                    )
                    cells.append({
                        "date": day,
                        "day": day.day,
                        "in_month": day.month == month,
                        "past": day < today,
                        "unavailable": unavailable,
                    })
                weeks.append(cells)
            resource_months.append({"label": date(year, month, 1).strftime("%B %Y"), "weeks": weeks})
        result[resource.id] = resource_months
    return result
