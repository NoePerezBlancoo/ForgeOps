from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.enums import IncidentStatus, Priority
from app.core.schemas import AssetSummary, ORMModel, UserSummary


class IncidentCreate(BaseModel):
    plant_id: UUID
    asset_id: UUID
    assigned_to: UUID | None = None
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    priority: Priority = Priority.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    downtime_minutes: int = Field(default=0, ge=0, le=525600)


class IncidentUpdate(BaseModel):
    assigned_to: UUID | None = None
    title: str | None = Field(default=None, min_length=5, max_length=180)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    priority: Priority | None = None
    status: IncidentStatus | None = None
    downtime_minutes: int | None = Field(default=None, ge=0, le=525600)
    root_cause: str | None = Field(default=None, max_length=4000)
    resolution: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_resolution(self):
        if self.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED} and not self.resolution:
            raise ValueError("La resolucion es obligatoria al resolver o cerrar una incidencia")
        return self


class IncidentRead(ORMModel):
    id: UUID
    company_id: UUID
    plant_id: UUID
    asset_id: UUID
    reported_by: UUID
    assigned_to: UUID | None
    title: str
    description: str
    priority: Priority
    status: IncidentStatus
    reported_at: datetime
    started_at: datetime | None
    resolved_at: datetime | None
    downtime_minutes: int
    root_cause: str | None
    resolution: str | None
    asset: AssetSummary
    reporter: UserSummary
    assignee: UserSummary | None
