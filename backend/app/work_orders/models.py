import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import (
    Priority,
    WorkOrderEventType,
    WorkOrderNoteType,
    WorkOrderParticipantRole,
    WorkOrderStatus,
    WorkOrderType,
    WorkSessionEndReason,
)
from app.core.mixins import TenantMixin, UUIDPrimaryKeyMixin


class WorkOrder(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        UniqueConstraint("company_id", "number", name="uq_work_orders_company_number"),
        Index("ix_work_orders_company_status", "company_id", "status"),
        Index("ix_work_orders_company_scheduled", "company_id", "scheduled_date"),
    )

    plant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), index=True
    )
    preventive_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("preventive_plans.id", ondelete="SET NULL"), index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[WorkOrderType] = mapped_column(
        Enum(WorkOrderType, name="work_order_type", native_enum=False, length=24),
        nullable=False,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="work_order_priority", native_enum=False, length=16),
        default=Priority.MEDIUM,
        nullable=False,
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        Enum(WorkOrderStatus, name="work_order_status", native_enum=False, length=24),
        default=WorkOrderStatus.OPEN,
        nullable=False,
    )
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_duration: Mapped[int | None] = mapped_column(Integer)
    real_duration: Mapped[int | None] = mapped_column(Integer)
    observations: Mapped[str | None] = mapped_column(Text)
    work_performed: Mapped[str | None] = mapped_column(Text)
    failure_cause: Mapped[str | None] = mapped_column(Text)
    root_cause: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="work_orders")  # noqa: F821
    incident: Mapped["Incident | None"] = relationship(back_populates="work_orders")  # noqa: F821
    preventive_plan: Mapped["PreventivePlan | None"] = relationship(  # noqa: F821
        back_populates="work_orders"
    )
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assigned_to])  # noqa: F821
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821
    validator: Mapped["User | None"] = relationship(foreign_keys=[validated_by])  # noqa: F821
    closer: Mapped["User | None"] = relationship(foreign_keys=[closed_by])  # noqa: F821
    participants: Mapped[list["WorkOrderParticipant"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="WorkOrderParticipant.joined_at",
        passive_deletes=True,
    )
    sessions: Mapped[list["WorkSession"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="WorkSession.started_at",
        passive_deletes=True,
    )
    notes: Mapped[list["WorkOrderNote"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="WorkOrderNote.created_at",
        passive_deletes=True,
    )
    events: Mapped[list["WorkOrderEvent"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="WorkOrderEvent.sequence_no",
        passive_deletes=True,
    )
    checklist_items: Mapped[list["WorkOrderChecklistItem"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="WorkOrderChecklistItem.position",
        passive_deletes=True,
    )

    __mapper_args__ = {"version_id_col": version}


class WorkOrderChecklistItem(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "work_order_checklist_items"
    __table_args__ = (
        UniqueConstraint("work_order_id", "position", name="uq_work_order_checklist_item_position"),
        CheckConstraint("position >= 1", name="ck_work_order_checklist_item_position"),
        Index("ix_work_order_checklist_item_completed", "work_order_id", "completed_at"),
        Index("ix_work_order_checklist_item_order_position", "work_order_id", "position"),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_template_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("checklist_template_items.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    work_order: Mapped[WorkOrder] = relationship(back_populates="checklist_items")
    source_template_item: Mapped["ChecklistTemplateItem | None"] = relationship()  # noqa: F821
    completer: Mapped["User | None"] = relationship(foreign_keys=[completed_by])  # noqa: F821

    __mapper_args__ = {"version_id_col": version}


class WorkOrderParticipant(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "work_order_participants"
    __table_args__ = (
        UniqueConstraint("work_order_id", "user_id", name="uq_work_order_participant_user"),
        Index("ix_work_order_participants_order_active", "work_order_id", "active"),
        Index("ix_work_order_participants_user_active", "company_id", "user_id", "active"),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    role: Mapped[WorkOrderParticipantRole] = mapped_column(
        Enum(
            WorkOrderParticipantRole,
            name="work_order_participant_role",
            native_enum=False,
            length=24,
        ),
        default=WorkOrderParticipantRole.TECHNICIAN,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    work_order: Mapped[WorkOrder] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
    assigner: Mapped["User | None"] = relationship(foreign_keys=[assigned_by])  # noqa: F821
    sessions: Mapped[list["WorkSession"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan", passive_deletes=True
    )


class WorkSession(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "work_sessions"
    __table_args__ = (
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_work_sessions_non_negative_duration",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name="ck_work_sessions_valid_interval"
        ),
        Index("ix_work_sessions_order_started", "work_order_id", "started_at"),
        Index("ix_work_sessions_user_started", "company_id", "user_id", "started_at"),
        Index(
            "uq_work_sessions_open_user_order",
            "work_order_id",
            "user_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order_participants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_reason: Mapped[WorkSessionEndReason | None] = mapped_column(
        Enum(
            WorkSessionEndReason,
            name="work_session_end_reason",
            native_enum=False,
            length=24,
        )
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    work_order: Mapped[WorkOrder] = relationship(back_populates="sessions")
    participant: Mapped[WorkOrderParticipant] = relationship(back_populates="sessions")
    user: Mapped["User"] = relationship()  # noqa: F821


class WorkOrderNote(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "work_order_notes"
    __table_args__ = (Index("ix_work_order_notes_order_created", "work_order_id", "created_at"),)

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note_type: Mapped[WorkOrderNoteType] = mapped_column(
        Enum(WorkOrderNoteType, name="work_order_note_type", native_enum=False, length=24),
        default=WorkOrderNoteType.COMMENT,
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    work_order: Mapped[WorkOrder] = relationship(back_populates="notes")
    author: Mapped["User | None"] = relationship()  # noqa: F821


class WorkOrderEvent(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "work_order_events"
    __table_args__ = (
        UniqueConstraint("work_order_id", "sequence_no", name="uq_work_order_event_sequence"),
        Index("ix_work_order_events_order_sequence", "work_order_id", "sequence_no"),
        Index("ix_work_order_events_company_occurred", "company_id", "occurred_at"),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[WorkOrderEventType] = mapped_column(
        Enum(WorkOrderEventType, name="work_order_event_type", native_enum=False, length=40),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    work_order: Mapped[WorkOrder] = relationship(back_populates="events")
    actor: Mapped["User | None"] = relationship()  # noqa: F821


def _prevent_history_mutation(mapper, connection, target) -> None:
    raise ValueError("El historial de intervencion es inmutable")


for immutable_model in (WorkOrderNote, WorkOrderEvent):
    event.listen(immutable_model, "before_update", _prevent_history_mutation)
    event.listen(immutable_model, "before_delete", _prevent_history_mutation)
