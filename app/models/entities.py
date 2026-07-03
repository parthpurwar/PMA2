from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, Enum):
    PMO = "PMO"
    PROJECT_LEAD = "PROJECT_LEAD"
    EMPLOYEE = "EMPLOYEE"


class RequestStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProjectStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"


class ExtensionStatus(str, Enum):
    NOT_DUE = "NOT_DUE"
    YET_TO_BE_UPDATED = "YET_TO_BE_UPDATED"
    EXTENSION_REQUIRED = "EXTENSION_REQUIRED"
    NO_EXTENSION_REQUIRED = "NO_EXTENSION_REQUIRED"


class BlockStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="lead")
    resource_profile: Mapped["Resource | None"] = relationship(back_populates="user", uselist=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(140), index=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    lead_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ProjectStatus] = mapped_column(SqlEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    lead: Mapped[User] = relationship(back_populates="projects")
    demands: Mapped[list["Demand"]] = relationship(back_populates="project")
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="project")


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True)
    employee_id: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(140), index=True)
    skill: Mapped[str] = mapped_column(String(80), index=True)
    role: Mapped[str] = mapped_column(String(80), default="Developer", index=True)
    level: Mapped[int] = mapped_column(Integer, index=True)
    location: Mapped[str] = mapped_column(String(80))
    current_allocation: Mapped[int] = mapped_column(Integer, default=0)
    reserved_allocation: Mapped[int] = mapped_column(Integer, default=0)
    available_from: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True)
    cv_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    additional_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_status: Mapped[str] = mapped_column(String(40), default="Available")
    education: Mapped[str | None] = mapped_column(Text, nullable=True)
    certifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_requested: Mapped[bool] = mapped_column(default=False)
    cv_request_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="resource_profile")
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="resource")
    blocks: Mapped[list["ResourceBlock"]] = relationship(back_populates="resource")


class Allocation(Base):
    __tablename__ = "allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    allocation_percent: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="Active")
    extension_status: Mapped[ExtensionStatus] = mapped_column(SqlEnum(ExtensionStatus), default=ExtensionStatus.NOT_DUE)
    extension_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    demand_id: Mapped[int | None] = mapped_column(ForeignKey("demands.id"), nullable=True)

    resource: Mapped[Resource] = relationship(back_populates="allocations")
    project: Mapped[Project] = relationship(back_populates="allocations")


class Demand(Base):
    __tablename__ = "demands"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    required_skill: Mapped[str] = mapped_column(String(80), index=True)
    required_role: Mapped[str] = mapped_column(String(80), default="Developer", index=True)
    required_level: Mapped[int] = mapped_column(Integer)
    number_of_resources: Mapped[int] = mapped_column(Integer)
    allocation_percent: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(30))
    remarks: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(SqlEnum(RequestStatus), default=RequestStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped[Project] = relationship(back_populates="demands")
    requested_by: Mapped[User] = relationship()
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="demand", cascade="all, delete-orphan")
    approvals: Mapped[list["ApprovalHistory"]] = relationship(back_populates="demand")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    demand_id: Mapped[int] = mapped_column(ForeignKey("demands.id"))
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    is_selected: Mapped[bool] = mapped_column(default=False)

    demand: Mapped[Demand] = relationship(back_populates="recommendations")
    resource: Mapped[Resource] = relationship()


class ApprovalHistory(Base):
    __tablename__ = "approval_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    demand_id: Mapped[int] = mapped_column(ForeignKey("demands.id"))
    action: Mapped[RequestStatus] = mapped_column(SqlEnum(RequestStatus))
    pmo_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    demand: Mapped[Demand] = relationship(back_populates="approvals")
    pmo: Mapped[User] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    pmo_username: Mapped[str] = mapped_column(String(60))
    project_lead_username: Mapped[str] = mapped_column(String(60))
    demand_id: Mapped[int] = mapped_column(Integer, index=True)
    old_allocation: Mapped[str] = mapped_column(Text)
    new_allocation: Mapped[str] = mapped_column(Text)
    resources_updated: Mapped[str] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    synced_by: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="SUCCESS")
    details: Mapped[str | None] = mapped_column(Text)


class ResourceBlock(Base):
    __tablename__ = "resource_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[BlockStatus] = mapped_column(SqlEnum(BlockStatus), default=BlockStatus.PENDING, index=True)
    pmo_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    pmo_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    resource: Mapped[Resource] = relationship(back_populates="blocks")
    requested_by: Mapped[User] = relationship(foreign_keys=[requested_by_id])
    project: Mapped[Project | None] = relationship()
    pmo: Mapped[User | None] = relationship(foreign_keys=[pmo_id])
