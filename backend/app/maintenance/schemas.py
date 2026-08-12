from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import FrequencyType, Priority
from app.core.schemas import AssetSummary, ORMModel, UserSummary


class PreventivePlanCreate(BaseModel):
    asset_id: UUID
    assigned_to: UUID | None = None
    name: str = Field(min_length=4, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    frequency_type: FrequencyType
    frequency_value: int = Field(ge=1, le=365)
    next_execution: datetime
    estimated_duration: int = Field(default=60, ge=1, le=10080)
    priority: Priority = Priority.MEDIUM
    active: bool = True


class PreventivePlanUpdate(BaseModel):
    assigned_to: UUID | None = None
    name: str | None = Field(default=None, min_length=4, max_length=180)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    frequency_type: FrequencyType | None = None
    frequency_value: int | None = Field(default=None, ge=1, le=365)
    next_execution: datetime | None = None
    estimated_duration: int | None = Field(default=None, ge=1, le=10080)
    priority: Priority | None = None
    active: bool | None = None


class PreventivePlanRead(ORMModel):
    id: UUID
    company_id: UUID
    asset_id: UUID
    assigned_to: UUID | None
    name: str
    description: str
    frequency_type: FrequencyType
    frequency_value: int
    next_execution: datetime
    estimated_duration: int
    priority: Priority
    active: bool
    last_generated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    asset: AssetSummary
    assignee: UserSummary | None


class GenerationSummary(BaseModel):
    generated: int
    skipped: int
