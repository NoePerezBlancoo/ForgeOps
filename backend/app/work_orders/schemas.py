from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.enums import Priority, WorkOrderStatus, WorkOrderType
from app.core.schemas import AssetSummary, ORMModel, UserSummary


class WorkOrderCreate(BaseModel):
    plant_id: UUID
    asset_id: UUID
    incident_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    type: WorkOrderType = WorkOrderType.CORRECTIVE
    priority: Priority = Priority.MEDIUM
    status: WorkOrderStatus = WorkOrderStatus.OPEN
    scheduled_date: datetime | None = None
    estimated_duration: int | None = Field(default=None, ge=1, le=10080)
    observations: str | None = Field(default=None, max_length=4000)


class WorkOrderUpdate(BaseModel):
    assigned_to: UUID | None = None
    title: str | None = Field(default=None, min_length=5, max_length=180)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    type: WorkOrderType | None = None
    priority: Priority | None = None
    status: WorkOrderStatus | None = None
    scheduled_date: datetime | None = None
    estimated_duration: int | None = Field(default=None, ge=1, le=10080)
    real_duration: int | None = Field(default=None, ge=1, le=10080)
    observations: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_completion(self):
        if self.status == WorkOrderStatus.COMPLETED and not self.real_duration:
            raise ValueError("La duracion real es obligatoria al completar una orden")
        return self


class WorkOrderRead(ORMModel):
    id: UUID
    company_id: UUID
    plant_id: UUID
    asset_id: UUID
    incident_id: UUID | None
    assigned_to: UUID | None
    created_by: UUID
    number: str
    title: str
    description: str
    type: WorkOrderType
    priority: Priority
    status: WorkOrderStatus
    scheduled_date: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    estimated_duration: int | None
    real_duration: int | None
    observations: str | None
    created_at: datetime
    asset: AssetSummary
    assignee: UserSummary | None
    creator: UserSummary
