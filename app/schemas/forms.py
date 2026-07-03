from datetime import date

from pydantic import BaseModel, Field, field_validator


class DemandCreate(BaseModel):
    project_id: int
    required_skill: str = Field(min_length=2, max_length=80)
    required_role: str = Field(min_length=2, max_length=80)
    required_level: int = Field(ge=1, le=5)
    number_of_resources: int = Field(ge=1, le=20)
    allocation_percent: int = Field(ge=1, le=100)
    start_date: date
    end_date: date
    priority: str = Field(min_length=3, max_length=30)
    remarks: str | None = Field(default=None, max_length=1000)

    @field_validator("end_date")
    @classmethod
    def end_must_follow_start(cls, end_date: date, info):
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("End date must be on or after start date.")
        return end_date


class RequestDecision(BaseModel):
    remarks: str | None = Field(default=None, max_length=1000)
