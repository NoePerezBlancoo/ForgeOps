import math
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.assets.models import Asset
from app.audit.service import add_audit_event
from app.core.enums import (
    NotificationType,
    Priority,
    UserRole,
    WorkOrderEventType,
    WorkOrderParticipantRole,
    WorkOrderStatus,
    WorkOrderType,
    WorkSessionEndReason,
)
from app.core.pagination import paginate
from app.incidents.models import Incident
from app.notifications.service import create_notification
from app.users.models import User
from app.work_orders.models import (
    WorkOrder,
    WorkOrderChecklistItem,
    WorkOrderEvent,
    WorkOrderNote,
    WorkOrderParticipant,
    WorkSession,
)
from app.work_orders.schemas import (
    WorkOrderChecklistItemUpdate,
    WorkOrderComplete,
    WorkOrderCreate,
    WorkOrderNoteCreate,
    WorkOrderParticipantCreate,
    WorkOrderReopen,
    WorkOrderUpdate,
    WorkOrderValidation,
    WorkSessionCommand,
)

MANAGER_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER}
PARTICIPANT_ROLES = MANAGER_ROLES | {UserRole.TECHNICIAN}


def _asset_for_company(db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.company_id == company_id))
    if not asset:
        raise HTTPException(status_code=422, detail="Activo no valido")
    return asset


def _participant_user(db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = db.scalar(
        select(User).where(User.id == user_id, User.company_id == company_id, User.active.is_(True))
    )
    if not user or user.role not in PARTICIPANT_ROLES:
        raise HTTPException(status_code=422, detail="Tecnico no valido")
    return user


def _base_query(detail: bool = False):
    options = [
        joinedload(WorkOrder.asset),
        joinedload(WorkOrder.assignee),
        joinedload(WorkOrder.creator),
    ]
    if detail:
        options.extend(
            [
                joinedload(WorkOrder.validator),
                joinedload(WorkOrder.closer),
                selectinload(WorkOrder.participants).joinedload(WorkOrderParticipant.user),
                selectinload(WorkOrder.participants).joinedload(WorkOrderParticipant.assigner),
                selectinload(WorkOrder.sessions).joinedload(WorkSession.user),
                selectinload(WorkOrder.notes).joinedload(WorkOrderNote.author),
                selectinload(WorkOrder.events).joinedload(WorkOrderEvent.actor),
                selectinload(WorkOrder.checklist_items).joinedload(
                    WorkOrderChecklistItem.completer
                ),
            ]
        )
    return select(WorkOrder).options(*options)


def _technician_scope(query, current_user: User):
    if current_user.role != UserRole.TECHNICIAN:
        return query
    return query.where(
        or_(
            WorkOrder.assigned_to == current_user.id,
            WorkOrder.participants.any(
                and_(
                    WorkOrderParticipant.user_id == current_user.id,
                    WorkOrderParticipant.active.is_(True),
                )
            ),
        )
    )


def list_work_orders(
    db: Session,
    current_user: User,
    search: str | None = None,
    order_status: WorkOrderStatus | None = None,
    priority: Priority | None = None,
    plant_id: uuid.UUID | None = None,
) -> list[WorkOrder]:
    query = _technician_scope(
        _base_query().where(WorkOrder.company_id == current_user.company_id), current_user
    )
    query = _apply_filters(query, search, order_status, priority, plant_id)
    return list(db.scalars(query.order_by(WorkOrder.created_at.desc()).limit(500)).unique())


def page_work_orders(
    db: Session,
    current_user: User,
    search: str | None,
    order_status: WorkOrderStatus | None,
    priority: Priority | None,
    plant_id: uuid.UUID | None,
    page: int,
    page_size: int,
    sort: str,
):
    query = _technician_scope(
        _base_query().where(WorkOrder.company_id == current_user.company_id), current_user
    )
    query = _apply_filters(query, search, order_status, priority, plant_id)
    order_by = {
        "created": WorkOrder.created_at.desc(),
        "scheduled": WorkOrder.scheduled_date.asc().nullslast(),
        "number": WorkOrder.number.desc(),
    }[sort]
    return paginate(
        db,
        query.order_by(order_by),
        page,
        page_size,
        sort,
        {
            "search": search,
            "status": order_status.value if order_status else None,
            "priority": priority.value if priority else None,
            "plant_id": str(plant_id) if plant_id else None,
        },
        unique=True,
    )


def _apply_filters(query, search, order_status, priority, plant_id):
    if search:
        term = f"%{search.strip()}%"
        query = query.join(WorkOrder.asset).where(
            or_(WorkOrder.number.ilike(term), WorkOrder.title.ilike(term), Asset.code.ilike(term))
        )
    if order_status:
        query = query.where(WorkOrder.status == order_status)
    if priority:
        query = query.where(WorkOrder.priority == priority)
    if plant_id:
        query = query.where(WorkOrder.plant_id == plant_id)
    return query


def get_work_order(db: Session, current_user: User, order_id: uuid.UUID) -> WorkOrder:
    return _get_work_order(db, current_user, order_id, detail=False)


def get_work_order_detail(db: Session, current_user: User, order_id: uuid.UUID) -> WorkOrder:
    return _get_work_order(db, current_user, order_id, detail=True)


def _get_work_order(
    db: Session, current_user: User, order_id: uuid.UUID, *, detail: bool
) -> WorkOrder:
    query = _technician_scope(
        _base_query(detail).where(
            WorkOrder.id == order_id, WorkOrder.company_id == current_user.company_id
        ),
        current_user,
    )
    order = db.scalar(query)
    if not order:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    return order


def _lock_order(db: Session, current_user: User, order_id: uuid.UUID) -> WorkOrder:
    order = db.scalar(
        select(WorkOrder)
        .where(WorkOrder.id == order_id, WorkOrder.company_id == current_user.company_id)
        .with_for_update()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    if current_user.role == UserRole.TECHNICIAN:
        participant = db.scalar(
            select(WorkOrderParticipant.id).where(
                WorkOrderParticipant.company_id == current_user.company_id,
                WorkOrderParticipant.work_order_id == order.id,
                WorkOrderParticipant.user_id == current_user.id,
                WorkOrderParticipant.active.is_(True),
            )
        )
        if order.assigned_to != current_user.id and not participant:
            raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    return order


def create_work_order(db: Session, current_user: User, payload: WorkOrderCreate) -> WorkOrder:
    asset = _asset_for_company(db, current_user.company_id, payload.asset_id)
    if asset.plant_id != payload.plant_id:
        raise HTTPException(status_code=422, detail="El activo no pertenece a la planta indicada")
    if payload.assigned_to:
        _participant_user(db, current_user.company_id, payload.assigned_to)
    if payload.incident_id:
        incident = db.scalar(
            select(Incident).where(
                Incident.id == payload.incident_id,
                Incident.company_id == current_user.company_id,
                Incident.asset_id == payload.asset_id,
            )
        )
        if not incident:
            raise HTTPException(status_code=422, detail="Incidencia vinculada no valida")
    values = payload.model_dump()
    values["status"] = WorkOrderStatus.ASSIGNED if payload.assigned_to else WorkOrderStatus.OPEN
    number = (
        f"{current_user.company.work_order_prefix}-"
        f"{datetime.now(UTC):%y%m}-{uuid.uuid4().hex[:6].upper()}"
    )
    order = WorkOrder(
        company_id=current_user.company_id,
        created_by=current_user.id,
        number=number,
        **values,
    )
    db.add(order)
    initialize_work_order_history(db, order, current_user)
    add_audit_event(
        db,
        order.company_id,
        current_user.id,
        "CREATE",
        "WORK_ORDER",
        f"Orden {order.number} creada",
        order.id,
    )
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def initialize_work_order_history(db: Session, order: WorkOrder, creator: User) -> WorkOrder:
    db.flush()
    existing = db.scalar(
        select(WorkOrderEvent.id).where(WorkOrderEvent.work_order_id == order.id).limit(1)
    )
    if existing:
        return order
    _append_event(
        db,
        order,
        creator,
        WorkOrderEventType.CREATED,
        "Orden de trabajo creada",
        {"status": order.status.value},
    )
    if order.assigned_to:
        participant = _upsert_participant(
            db,
            order,
            order.assigned_to,
            WorkOrderParticipantRole.LEAD,
            creator.id,
        )
        assignment_event = _append_event(
            db,
            order,
            creator,
            WorkOrderEventType.ASSIGNED,
            f"{participant.user.full_name} asignado como tecnico principal",
            {"user_id": str(participant.user_id)},
        )
        _notify_assignment(db, order, participant.user_id, assignment_event.id)
    return order


def update_work_order(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkOrderUpdate,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return get_work_order_detail(db, current_user, order.id)
    if current_user.role == UserRole.TECHNICIAN and set(changes) - {"observations"}:
        raise HTTPException(
            status_code=403,
            detail="El tecnico registra la ejecucion mediante acciones y notas",
        )
    if order.status in {
        WorkOrderStatus.PENDING_VALIDATION,
        WorkOrderStatus.COMPLETED,
        WorkOrderStatus.CLOSED,
        WorkOrderStatus.CANCELLED,
    }:
        raise HTTPException(status_code=409, detail="La orden finalizada no se puede editar")
    previous_assignee = order.assigned_to
    if "assigned_to" in changes and changes["assigned_to"]:
        _participant_user(db, current_user.company_id, changes["assigned_to"])
    for field, value in changes.items():
        setattr(order, field, value)
    if "assigned_to" in changes and changes["assigned_to"] != previous_assignee:
        new_assignee = changes["assigned_to"]
        if new_assignee:
            participant = _upsert_participant(
                db,
                order,
                new_assignee,
                WorkOrderParticipantRole.LEAD,
                current_user.id,
            )
            summary = f"{participant.user.full_name} asignado como tecnico principal"
        else:
            previous_lead = db.scalar(
                select(WorkOrderParticipant).where(
                    WorkOrderParticipant.work_order_id == order.id,
                    WorkOrderParticipant.user_id == previous_assignee,
                    WorkOrderParticipant.active.is_(True),
                )
            )
            if previous_lead:
                previous_lead.role = WorkOrderParticipantRole.TECHNICIAN
            summary = "Orden sin tecnico principal"
        if order.status in {WorkOrderStatus.OPEN, WorkOrderStatus.ASSIGNED}:
            order.status = WorkOrderStatus.ASSIGNED if new_assignee else WorkOrderStatus.OPEN
        assignment_event = _append_event(
            db,
            order,
            current_user,
            WorkOrderEventType.ASSIGNED,
            summary,
            {
                "previous_user_id": str(previous_assignee) if previous_assignee else None,
                "user_id": str(new_assignee) if new_assignee else None,
            },
        )
        if new_assignee:
            _notify_assignment(db, order, new_assignee, assignment_event.id)
    else:
        _append_event(
            db,
            order,
            current_user,
            WorkOrderEventType.UPDATED,
            "Datos de la orden actualizados",
            {"fields": sorted(changes)},
        )
    add_audit_event(
        db,
        order.company_id,
        current_user.id,
        "UPDATE",
        "WORK_ORDER",
        f"Orden {order.number} actualizada",
        order.id,
        {"fields": sorted(changes)},
    )
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def add_participant(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkOrderParticipantCreate,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    if order.status not in {
        WorkOrderStatus.OPEN,
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.WAITING,
    }:
        raise HTTPException(status_code=409, detail="La orden no admite participantes")
    user = _participant_user(db, order.company_id, payload.user_id)
    participant = _upsert_participant(db, order, user.id, payload.role, current_user.id)
    if payload.role == WorkOrderParticipantRole.LEAD:
        order.assigned_to = user.id
        if order.status == WorkOrderStatus.OPEN:
            order.status = WorkOrderStatus.ASSIGNED
    assignment_event = _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.PARTICIPANT_ADDED,
        f"{user.full_name} incorporado a la intervencion",
        {"user_id": str(user.id), "role": participant.role.value},
    )
    _notify_assignment(db, order, user.id, assignment_event.id)
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def remove_participant(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    participant_id: uuid.UUID,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    if order.status not in {
        WorkOrderStatus.OPEN,
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.WAITING,
    }:
        raise HTTPException(status_code=409, detail="La orden no admite cambios de equipo")
    participant = db.scalar(
        select(WorkOrderParticipant)
        .options(joinedload(WorkOrderParticipant.user))
        .where(
            WorkOrderParticipant.id == participant_id,
            WorkOrderParticipant.company_id == order.company_id,
            WorkOrderParticipant.work_order_id == order.id,
            WorkOrderParticipant.active.is_(True),
        )
        .with_for_update()
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    now = datetime.now(UTC)
    session = _open_session(db, order.id, participant.user_id, lock=True)
    if session:
        _finish_session(session, now, WorkSessionEndReason.REMOVED)
        db.flush()
        remaining = db.scalar(
            select(func.count(WorkSession.id)).where(
                WorkSession.work_order_id == order.id,
                WorkSession.ended_at.is_(None),
            )
        )
        if order.status == WorkOrderStatus.IN_PROGRESS and not remaining:
            order.status = WorkOrderStatus.WAITING
    participant.active = False
    participant.removed_at = now
    if order.assigned_to == participant.user_id:
        order.assigned_to = None
        if order.status == WorkOrderStatus.ASSIGNED:
            order.status = WorkOrderStatus.OPEN
    _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.PARTICIPANT_REMOVED,
        f"{participant.user.full_name} retirado de la intervencion",
        {"user_id": str(participant.user_id)},
    )
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def start_work(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkSessionCommand,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    if order.status not in {
        WorkOrderStatus.OPEN,
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.WAITING,
        WorkOrderStatus.IN_PROGRESS,
    }:
        raise HTTPException(status_code=409, detail="La orden no se puede iniciar")
    participant = _active_participant(db, order, current_user)
    if _open_session(db, order.id, current_user.id, lock=True):
        raise HTTPException(status_code=409, detail="Ya existe una sesion de trabajo activa")
    previous_sessions = db.scalar(
        select(func.count(WorkSession.id)).where(
            WorkSession.work_order_id == order.id,
            WorkSession.user_id == current_user.id,
        )
    )
    now = datetime.now(UTC)
    db.add(
        WorkSession(
            company_id=order.company_id,
            work_order_id=order.id,
            participant_id=participant.id,
            user_id=current_user.id,
            started_at=now,
        )
    )
    order.status = WorkOrderStatus.IN_PROGRESS
    if not order.started_at:
        order.started_at = now
    event_type = WorkOrderEventType.RESUMED if previous_sessions else WorkOrderEventType.STARTED
    verb = "reanudado" if previous_sessions else "iniciado"
    _append_event(
        db,
        order,
        current_user,
        event_type,
        f"{current_user.full_name} ha {verb} la intervencion",
        {"user_id": str(current_user.id)},
    )
    if payload.note:
        _add_note(db, order, current_user, WorkOrderNoteCreate(body=payload.note))
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def pause_work(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkSessionCommand,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    _active_participant(db, order, current_user)
    session = _open_session(db, order.id, current_user.id, lock=True)
    if not session:
        raise HTTPException(status_code=409, detail="No existe una sesion activa")
    now = datetime.now(UTC)
    _finish_session(session, now, WorkSessionEndReason.PAUSED)
    db.flush()
    remaining = db.scalar(
        select(func.count(WorkSession.id)).where(
            WorkSession.work_order_id == order.id, WorkSession.ended_at.is_(None)
        )
    )
    if not remaining:
        order.status = WorkOrderStatus.WAITING
    _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.PAUSED,
        f"{current_user.full_name} ha pausado la intervencion",
        {"user_id": str(current_user.id), "duration_seconds": session.duration_seconds},
    )
    if payload.note:
        _add_note(db, order, current_user, WorkOrderNoteCreate(body=payload.note))
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def add_note(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkOrderNoteCreate,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    if current_user.role == UserRole.TECHNICIAN:
        _active_participant(db, order, current_user)
    _add_note(db, order, current_user, payload)
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def update_checklist_item(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: WorkOrderChecklistItemUpdate,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    if current_user.role == UserRole.TECHNICIAN:
        _active_participant(db, order, current_user)
    if order.status not in {
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.WAITING,
    }:
        raise HTTPException(status_code=409, detail="La orden no admite cambios de checklist")
    item = db.scalar(
        select(WorkOrderChecklistItem)
        .where(
            WorkOrderChecklistItem.id == item_id,
            WorkOrderChecklistItem.work_order_id == order.id,
            WorkOrderChecklistItem.company_id == current_user.company_id,
        )
        .with_for_update()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Paso de checklist no encontrado")
    if item.version != payload.version:
        raise HTTPException(
            status_code=409,
            detail="El checklist ha cambiado. Recarga la orden antes de continuar",
        )
    now = datetime.now(UTC)
    item.completed_at = now if payload.completed else None
    item.completed_by = current_user.id if payload.completed else None
    item.notes = payload.notes.strip() if payload.notes and payload.notes.strip() else None
    action = "completado" if payload.completed else "reabierto"
    _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.CHECKLIST_UPDATED,
        f"{current_user.full_name} ha {action}: {item.title}",
        {
            "checklist_item_id": str(item.id),
            "completed": payload.completed,
            "notes": item.notes,
        },
    )
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def complete_work(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkOrderComplete,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    participant = _active_participant(db, order, current_user)
    if current_user.role == UserRole.TECHNICIAN and (
        participant.role != WorkOrderParticipantRole.LEAD and order.assigned_to != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Solo el tecnico principal puede finalizar")
    if order.status not in {
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.WAITING,
    }:
        raise HTTPException(status_code=409, detail="La orden no se puede finalizar")
    incomplete_required = db.scalar(
        select(func.count(WorkOrderChecklistItem.id)).where(
            WorkOrderChecklistItem.work_order_id == order.id,
            WorkOrderChecklistItem.required.is_(True),
            WorkOrderChecklistItem.completed_at.is_(None),
        )
    ) or 0
    if incomplete_required:
        raise HTTPException(
            status_code=409,
            detail=f"Quedan {incomplete_required} pasos obligatorios del checklist",
        )
    work_performed = payload.work_performed.strip()
    failure_cause = (payload.failure_cause or "").strip()
    resolution = (payload.resolution or "").strip()
    if len(work_performed) < 10:
        raise HTTPException(status_code=422, detail="El trabajo realizado requiere mas detalle")
    if order.type == WorkOrderType.CORRECTIVE and (
        len(failure_cause) < 3 or len(resolution) < 5
    ):
        raise HTTPException(
            status_code=422,
            detail="Las ordenes correctivas requieren causa y solucion",
        )
    now = datetime.now(UTC)
    sessions = list(
        db.scalars(
            select(WorkSession)
            .where(WorkSession.work_order_id == order.id, WorkSession.ended_at.is_(None))
            .with_for_update()
        )
    )
    for session in sessions:
        _finish_session(session, now, WorkSessionEndReason.COMPLETED)
    db.flush()
    total_seconds = db.scalar(
        select(func.coalesce(func.sum(WorkSession.duration_seconds), 0)).where(
            WorkSession.work_order_id == order.id
        )
    )
    order.status = WorkOrderStatus.PENDING_VALIDATION
    order.completed_at = now
    order.real_duration = max(1, math.ceil((total_seconds or 0) / 60))
    order.work_performed = work_performed
    order.failure_cause = failure_cause or None
    order.root_cause = payload.root_cause.strip() if payload.root_cause else None
    order.resolution = resolution or None
    if payload.observations is not None:
        order.observations = payload.observations
    participant_count = db.scalar(
        select(func.count(func.distinct(WorkSession.user_id))).where(
            WorkSession.work_order_id == order.id
        )
    )
    _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.COMPLETED,
        f"{current_user.full_name} ha finalizado la intervencion",
        {
            "duration_minutes": order.real_duration,
            "participants": participant_count or 0,
            "work_performed": order.work_performed,
            "failure_cause": order.failure_cause,
            "root_cause": order.root_cause,
            "resolution": order.resolution,
        },
    )
    add_audit_event(
        db,
        order.company_id,
        current_user.id,
        "COMPLETE",
        "WORK_ORDER",
        f"Orden {order.number} pendiente de validacion",
        order.id,
    )
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def validate_work(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkOrderValidation,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    if order.status != WorkOrderStatus.PENDING_VALIDATION:
        raise HTTPException(status_code=409, detail="La orden no esta pendiente de validacion")
    now = datetime.now(UTC)
    order.status = WorkOrderStatus.COMPLETED
    order.validated_by = current_user.id
    order.validated_at = now
    _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.VALIDATED,
        f"{current_user.full_name} ha validado el trabajo",
        {},
    )
    if payload.note:
        _add_note(db, order, current_user, WorkOrderNoteCreate(body=payload.note))
    add_audit_event(
        db,
        order.company_id,
        current_user.id,
        "VALIDATE",
        "WORK_ORDER",
        f"Orden {order.number} validada",
        order.id,
    )
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def close_work(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkOrderValidation,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    if order.status != WorkOrderStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="La orden debe estar validada antes de cerrar")
    now = datetime.now(UTC)
    order.status = WorkOrderStatus.CLOSED
    order.closed_by = current_user.id
    order.closed_at = now
    _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.CLOSED,
        f"{current_user.full_name} ha cerrado la orden",
        {},
    )
    if payload.note:
        _add_note(db, order, current_user, WorkOrderNoteCreate(body=payload.note))
    add_audit_event(
        db,
        order.company_id,
        current_user.id,
        "CLOSE",
        "WORK_ORDER",
        f"Orden {order.number} cerrada",
        order.id,
    )
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def reopen_work(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkOrderReopen,
) -> WorkOrder:
    order = _lock_order(db, current_user, order_id)
    if order.status not in {
        WorkOrderStatus.PENDING_VALIDATION,
        WorkOrderStatus.COMPLETED,
        WorkOrderStatus.CLOSED,
    }:
        raise HTTPException(status_code=409, detail="La orden no se puede reabrir")
    previous_status = order.status
    order.status = WorkOrderStatus.ASSIGNED if order.assigned_to else WorkOrderStatus.OPEN
    order.completed_at = None
    order.validated_by = None
    order.validated_at = None
    order.closed_by = None
    order.closed_at = None
    _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.REOPENED,
        f"{current_user.full_name} ha reabierto la orden",
        {"previous_status": previous_status.value, "reason": payload.reason},
    )
    _add_note(db, order, current_user, WorkOrderNoteCreate(body=payload.reason))
    add_audit_event(
        db,
        order.company_id,
        current_user.id,
        "REOPEN",
        "WORK_ORDER",
        f"Orden {order.number} reabierta",
        order.id,
    )
    db.commit()
    return get_work_order_detail(db, current_user, order.id)


def _active_participant(db: Session, order: WorkOrder, current_user: User) -> WorkOrderParticipant:
    participant = db.scalar(
        select(WorkOrderParticipant)
        .where(
            WorkOrderParticipant.company_id == order.company_id,
            WorkOrderParticipant.work_order_id == order.id,
            WorkOrderParticipant.user_id == current_user.id,
            WorkOrderParticipant.active.is_(True),
        )
        .with_for_update()
    )
    if participant:
        return participant
    if order.assigned_to == current_user.id:
        return _upsert_participant(
            db,
            order,
            current_user.id,
            WorkOrderParticipantRole.LEAD,
            order.created_by,
        )
    raise HTTPException(status_code=403, detail="No participas en esta intervencion")


def _upsert_participant(
    db: Session,
    order: WorkOrder,
    user_id: uuid.UUID,
    role: WorkOrderParticipantRole,
    assigned_by: uuid.UUID,
) -> WorkOrderParticipant:
    user = _participant_user(db, order.company_id, user_id)
    if role == WorkOrderParticipantRole.LEAD:
        leads = list(
            db.scalars(
                select(WorkOrderParticipant).where(
                    WorkOrderParticipant.work_order_id == order.id,
                    WorkOrderParticipant.role == WorkOrderParticipantRole.LEAD,
                    WorkOrderParticipant.user_id != user_id,
                    WorkOrderParticipant.active.is_(True),
                )
            )
        )
        for lead in leads:
            lead.role = WorkOrderParticipantRole.TECHNICIAN
    participant = db.scalar(
        select(WorkOrderParticipant).where(
            WorkOrderParticipant.company_id == order.company_id,
            WorkOrderParticipant.work_order_id == order.id,
            WorkOrderParticipant.user_id == user_id,
        )
    )
    if participant:
        participant.role = role
        participant.active = True
        participant.removed_at = None
        participant.assigned_by = assigned_by
    else:
        participant = WorkOrderParticipant(
            company_id=order.company_id,
            work_order_id=order.id,
            user_id=user_id,
            assigned_by=assigned_by,
            role=role,
        )
        db.add(participant)
    participant.user = user
    db.flush()
    return participant


def _open_session(
    db: Session, order_id: uuid.UUID, user_id: uuid.UUID, *, lock: bool
) -> WorkSession | None:
    query = select(WorkSession).where(
        WorkSession.work_order_id == order_id,
        WorkSession.user_id == user_id,
        WorkSession.ended_at.is_(None),
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _finish_session(session: WorkSession, ended_at: datetime, reason: WorkSessionEndReason) -> None:
    started_at = session.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    session.ended_at = ended_at
    session.ended_reason = reason
    session.duration_seconds = max(0, int((ended_at - started_at).total_seconds()))


def _add_note(
    db: Session,
    order: WorkOrder,
    current_user: User,
    payload: WorkOrderNoteCreate,
) -> WorkOrderNote:
    note = WorkOrderNote(
        company_id=order.company_id,
        work_order_id=order.id,
        author_id=current_user.id,
        note_type=payload.note_type,
        body=payload.body.strip(),
    )
    if len(note.body) < 2:
        raise HTTPException(status_code=422, detail="La nota no puede estar vacia")
    db.add(note)
    db.flush()
    _append_event(
        db,
        order,
        current_user,
        WorkOrderEventType.NOTE_ADDED,
        f"{current_user.full_name} ha anadido una nota",
        {"note_id": str(note.id), "note_type": note.note_type.value},
    )
    return note


def _append_event(
    db: Session,
    order: WorkOrder,
    actor: User | None,
    event_type: WorkOrderEventType,
    summary: str,
    details: dict,
) -> WorkOrderEvent:
    sequence = db.scalar(
        select(func.coalesce(func.max(WorkOrderEvent.sequence_no), 0)).where(
            WorkOrderEvent.work_order_id == order.id
        )
    )
    timeline_event = WorkOrderEvent(
        company_id=order.company_id,
        work_order_id=order.id,
        actor_id=actor.id if actor else None,
        sequence_no=(sequence or 0) + 1,
        event_type=event_type,
        summary=summary,
        details=details,
        occurred_at=datetime.now(UTC),
    )
    db.add(timeline_event)
    db.flush()
    return timeline_event


def _notify_assignment(
    db: Session,
    order: WorkOrder,
    recipient_id: uuid.UUID,
    event_id: uuid.UUID,
) -> None:
    create_notification(
        db,
        company_id=order.company_id,
        recipient_id=recipient_id,
        notification_type=NotificationType.WORK_ORDER_ASSIGNED,
        title=f"Trabajo asignado: {order.number}",
        body=order.title,
        href=f"/work-orders?order={order.id}",
        dedupe_key=f"work-order-assignment:{event_id}",
    )
