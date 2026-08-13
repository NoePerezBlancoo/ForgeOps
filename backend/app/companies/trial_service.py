from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.audit.service import add_audit_event
from app.auth.schemas import TrialRegistration
from app.auth.security import hash_password
from app.companies.models import DEFAULT_COMPANY_MODULES, Company
from app.core.config import settings
from app.core.database import set_database_context
from app.core.enums import (
    AssetStatus,
    CompanyPlan,
    Criticality,
    FrequencyType,
    IncidentStatus,
    InventoryMovementType,
    Priority,
    SubscriptionStatus,
    UserRole,
    WorkOrderStatus,
    WorkOrderType,
)
from app.incidents.models import Incident
from app.inventory.models import InventoryItem, InventoryMovement
from app.maintenance.models import PreventivePlan
from app.plants.models import Plant
from app.users.models import User
from app.work_orders.models import WorkOrder
from app.work_orders.service import initialize_work_order_history


def register_trial(db: Session, payload: TrialRegistration) -> User:
    set_database_context(db, "signup")
    if not settings.trial_signup_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El alta automatica de pruebas no esta disponible en este momento",
        )
    if db.scalar(select(User.id).where(User.email == payload.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con este correo electronico",
        )

    now = datetime.now(UTC)
    company = Company(
        name=payload.company_name,
        tax_id=None,
        email=payload.email,
        industry=payload.industry,
        timezone="Europe/Madrid",
        locale="es-ES",
        work_order_prefix="OT",
        plan=CompanyPlan.TRIAL,
        subscription_status=SubscriptionStatus.TRIAL,
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=settings.trial_days),
        enabled_modules=list(DEFAULT_COMPANY_MODULES),
        active=True,
    )
    db.add(company)
    db.flush()
    set_database_context(db, "tenant", company.id)

    user = User(
        company_id=company.id,
        full_name=payload.full_name,
        email=payload.email,
        job_title="Administrador de ForgeOps",
        password_hash=hash_password(payload.password),
        password_changed_at=now,
        role=UserRole.ADMIN,
        active=True,
    )
    user.company = company
    db.add(user)
    db.flush()

    plant = Plant(
        company_id=company.id,
        name=payload.plant_name,
        code="PLANTA-01",
        description="Planta principal creada durante la configuracion inicial.",
        active=True,
    )
    db.add(plant)
    db.flush()

    if payload.sample_data:
        _add_sample_data(db, company, plant, user, now)

    add_audit_event(
        db,
        company.id,
        user.id,
        "TRIAL_CREATED",
        "COMPANY",
        f"Prueba de {settings.trial_days} dias iniciada",
        company.id,
        {"sample_data": payload.sample_data},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo crear la prueba con los datos indicados",
        ) from exc
    return user


def _add_sample_data(
    db: Session,
    company: Company,
    plant: Plant,
    user: User,
    now: datetime,
) -> None:
    assets = [
        Asset(
            company_id=company.id,
            plant_id=plant.id,
            code="CMP-001",
            name="Compresor principal",
            manufacturer="Atlas Copco",
            model="GA 30",
            status=AssetStatus.ACTIVE,
            criticality=Criticality.CRITICAL,
            location="Sala tecnica",
        ),
        Asset(
            company_id=company.id,
            plant_id=plant.id,
            code="LIN-001",
            name="Linea de produccion",
            manufacturer="Bosch Rexroth",
            status=AssetStatus.STOPPED,
            criticality=Criticality.HIGH,
            location="Produccion",
        ),
        Asset(
            company_id=company.id,
            plant_id=plant.id,
            code="CDE-001",
            name="Cuadro electrico general",
            status=AssetStatus.ACTIVE,
            criticality=Criticality.HIGH,
            location="Sala electrica",
        ),
    ]
    db.add_all(assets)
    db.flush()

    incident = Incident(
        company_id=company.id,
        plant_id=plant.id,
        asset_id=assets[1].id,
        reported_by=user.id,
        title="Parada intermitente de la linea",
        description="La linea se detiene de forma intermitente durante el ciclo automatico.",
        priority=Priority.HIGH,
        status=IncidentStatus.OPEN,
        reported_at=now - timedelta(hours=2),
        downtime_minutes=45,
    )
    db.add(incident)
    db.flush()

    work_orders = [
        WorkOrder(
            company_id=company.id,
            plant_id=plant.id,
            asset_id=assets[1].id,
            incident_id=incident.id,
            created_by=user.id,
            number="OT-0001",
            title="Diagnosticar parada intermitente",
            description="Revisar sensores, seguridades y secuencia del automatismo.",
            type=WorkOrderType.CORRECTIVE,
            priority=Priority.HIGH,
            status=WorkOrderStatus.OPEN,
            scheduled_date=now + timedelta(days=1),
            estimated_duration=90,
        ),
        WorkOrder(
            company_id=company.id,
            plant_id=plant.id,
            asset_id=assets[0].id,
            assigned_to=user.id,
            created_by=user.id,
            number="OT-0002",
            title="Revision inicial del compresor",
            description="Comprobar niveles, filtros, fugas y parametros de servicio.",
            type=WorkOrderType.INSPECTION,
            priority=Priority.MEDIUM,
            status=WorkOrderStatus.ASSIGNED,
            scheduled_date=now + timedelta(days=3),
            estimated_duration=60,
        ),
    ]
    db.add_all(work_orders)
    for order in work_orders:
        initialize_work_order_history(db, order, user)
    db.add(
        PreventivePlan(
            company_id=company.id,
            asset_id=assets[0].id,
            name="Revision mensual del compresor",
            description="Inspeccion de niveles, filtros, fugas y temperatura de trabajo.",
            frequency_type=FrequencyType.MONTHS,
            frequency_value=1,
            next_execution=now + timedelta(days=14),
            estimated_duration=60,
            priority=Priority.HIGH,
            active=True,
        )
    )

    items = [
        InventoryItem(
            company_id=company.id,
            code="SENS-M18",
            name="Sensor inductivo M18",
            stock=Decimal("3"),
            minimum_stock=Decimal("2"),
            unit="ud",
            location="A-01",
            active=True,
        ),
        InventoryItem(
            company_id=company.id,
            code="FILT-CMP",
            name="Filtro de aceite de compresor",
            stock=Decimal("1"),
            minimum_stock=Decimal("2"),
            unit="ud",
            location="A-02",
            active=True,
        ),
    ]
    db.add_all(items)
    db.flush()
    db.add_all(
        [
            InventoryMovement(
                company_id=company.id,
                item_id=item.id,
                user_id=user.id,
                movement_type=InventoryMovementType.RECEIPT,
                quantity=item.stock,
                resulting_stock=item.stock,
                reason="Stock inicial de la prueba",
            )
            for item in items
        ]
    )
