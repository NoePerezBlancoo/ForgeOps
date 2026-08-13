from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import (
    Priority,
    WorkOrderEventType,
    WorkOrderNoteType,
    WorkOrderParticipantRole,
    WorkOrderStatus,
    WorkOrderType,
    WorkSessionEndReason,
)
from app.core.schemas import AssetSummary, ORMModel, UserSummary
from app.inventory.schemas import InventoryMovementRead


class WorkOrderChecklistItemUpdate(BaseModel):
    completed: bool
    notes: str | None = Field(default=None, max_length=4000)
    version: int = Field(ge=1)


class WorkOrderChecklistItemRead(ORMModel):
    id: UUID
    company_id: UUID
    work_order_id: UUID
    source_template_item_id: UUID | None
    title: str
    instructions: str | None
    position: int
    required: bool
    completed_by: UUID | None
    completed_at: datetime | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    completer: UserSummary | None


class WorkOrderCreate(BaseModel):
    plant_id: UUID
    asset_id: UUID
    incident_id: UUID | None = None
    assigned_to: UUID | None = None
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    type: WorkOrderType = WorkOrderType.CORRECTIVE
    priority: Priority = Priority.MEDIUM
    scheduled_date: datetime | None = None
    estimated_duration: int | None = Field(default=None, ge=1, le=10080)
    observations: str | None = Field(default=None, max_length=4000)


class WorkOrderUpdate(BaseModel):
    assigned_to: UUID | None = None
    title: str | None = Field(default=None, min_length=5, max_length=180)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    type: WorkOrderType | None = None
    priority: Priority | None = None
    scheduled_date: datetime | None = None
    estimated_duration: int | None = Field(default=None, ge=1, le=10080)
    observations: str | None = Field(default=None, max_length=4000)


class WorkOrderRead(ORMModel):
    id: UUID
    company_id: UUID
    plant_id: UUID
    asset_id: UUID
    incident_id: UUID | None
    preventive_plan_id: UUID | None
    assigned_to: UUID | None
    created_by: UUID
    validated_by: UUID | None
    closed_by: UUID | None
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
    work_performed: str | None
    failure_cause: str | None
    root_cause: str | None
    resolution: str | None
    validated_at: datetime | None
    closed_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    asset: AssetSummary
    assignee: UserSummary | None
    creator: UserSummary


class WorkOrderParticipantCreate(BaseModel):
    user_id: UUID
    role: WorkOrderParticipantRole = WorkOrderParticipantRole.TECHNICIAN


class WorkOrderParticipantRead(ORMModel):
    id: UUID
    user_id: UUID
    assigned_by: UUID | None
    role: WorkOrderParticipantRole
    active: bool
    joined_at: datetime
    removed_at: datetime | None
    user: UserSummary
    assigner: UserSummary | None


class WorkSessionRead(ORMModel):
    id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: datetime | None
    ended_reason: WorkSessionEndReason | None
    duration_seconds: int | None
    user: UserSummary


class WorkOrderNoteCreate(BaseModel):
    note_type: WorkOrderNoteType = WorkOrderNoteType.COMMENT
    body: str = Field(min_length=2, max_length=4000)


class WorkOrderNoteRead(ORMModel):
    id: UUID
    author_id: UUID | None
    note_type: WorkOrderNoteType
    body: str
    created_at: datetime
    author: UserSummary | None


class WorkOrderEventRead(ORMModel):
    id: UUID
    actor_id: UUID | None
    sequence_no: int
    event_type: WorkOrderEventType
    summary: str
    details: dict
    occurred_at: datetime
    actor: UserSummary | None


class WorkOrderDetailRead(WorkOrderRead):
    validator: UserSummary | None
    closer: UserSummary | None
    participants: list[WorkOrderParticipantRead]
    sessions: list[WorkSessionRead]
    notes: list[WorkOrderNoteRead]
    events: list[WorkOrderEventRead]
    checklist_items: list[WorkOrderChecklistItemRead]
    inventory_movements: list[InventoryMovementRead]
    material_cost: Decimal


class WorkSessionCommand(BaseModel):
    note: str | None = Field(default=None, min_length=2, max_length=1000)


class WorkOrderComplete(BaseModel):
    work_performed: str = Field(min_length=10, max_length=8000)
    failure_cause: str | None = Field(default=None, max_length=4000)
    root_cause: str | None = Field(default=None, max_length=4000)
    resolution: str | None = Field(default=None, max_length=8000)
    observations: str | None = Field(default=None, max_length=4000)


class WorkOrderValidation(BaseModel):
    note: str | None = Field(default=None, min_length=2, max_length=2000)


class WorkOrderReopen(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


class WorkOrderMaterialConsume(BaseModel):
    item_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, min_length=4, max_length=255)


class WorkOrderMaterialReturn(BaseModel):
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, min_length=4, max_length=255)
