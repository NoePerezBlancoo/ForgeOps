from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.audit.service import add_audit_event
from app.core.enums import CompanyModule, UserRole
from app.incidents.models import Incident
from app.onboarding.models import OnboardingProgress
from app.onboarding.schemas import OnboardingRead, OnboardingStepRead, OnboardingUpdate
from app.plants.models import Plant
from app.users.models import User
from app.work_orders.models import WorkOrder

MANUAL_STEPS = {"WELCOME", "MODULES", "TOUR"}


def get_onboarding(db: Session, current_user: User) -> OnboardingRead:
    progress = _get_or_create_progress(db, current_user)
    company_id = current_user.company_id
    manual = set(progress.completed_steps)
    is_admin = current_user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}

    steps = [
        _step(
            "WELCOME",
            "Conoce tu centro de operaciones",
            "Revisa el flujo principal y elige la planta sobre la que vas a trabajar.",
            "/getting-started",
            "WELCOME" in manual,
            False,
        )
    ]
    if is_admin:
        profile_ready = bool(current_user.company.tax_id and current_user.company.industry)
        steps.append(
            _step(
                "COMPANY",
                "Completa los datos de empresa",
                "Configura identificacion, contacto, zona horaria y numeracion de ordenes.",
                "/company",
                profile_ready,
                True,
            )
        )
    steps.extend(
        [
            _step(
                "PLANT",
                "Prepara una planta",
                "Crea el centro de trabajo que agrupara activos y operaciones.",
                "/plants",
                _count(db, Plant, company_id) > 0,
                True,
            ),
            _step(
                "ASSET",
                "Registra el primer activo",
                "Identifica un equipo critico con ubicacion, estado y fabricante.",
                "/assets",
                _count(db, Asset, company_id) > 0,
                True,
            ),
            _step(
                "INCIDENT",
                "Registra una incidencia",
                "Documenta una averia y su impacto para iniciar la trazabilidad.",
                "/incidents?new=1",
                _count(db, Incident, company_id) > 0,
                True,
            ),
            _step(
                "WORK_ORDER",
                "Planifica una orden de trabajo",
                "Asigna la intervencion y sigue su estado hasta el cierre.",
                "/work-orders",
                _count(db, WorkOrder, company_id) > 0,
                True,
            ),
        ]
    )
    if is_admin:
        steps.extend(
            [
                _step(
                    "TEAM",
                    "Invita al equipo",
                    "Crea al menos otro usuario y asigna el permiso adecuado.",
                    "/users",
                    _count(db, User, company_id) >= 2,
                    True,
                ),
                _step(
                    "MODULES",
                    "Elige los modulos de trabajo",
                    "Adapta la navegacion a los procesos que utiliza tu empresa.",
                    "/modules",
                    "MODULES" in manual,
                    False,
                ),
            ]
        )
    if CompanyModule.DOCUMENTS.value in current_user.company.enabled_modules:
        steps.append(
            _step(
                "TOUR",
                "Completa la guia operativa",
                "Consulta el tutorial de incidencias, ordenes, preventivos y documentos.",
                "/getting-started#guide",
                progress.tour_completed_at is not None or "TOUR" in manual,
                False,
            )
        )

    completed = sum(step.complete for step in steps)
    total = len(steps)
    return OnboardingRead(
        completed=completed,
        total=total,
        percent=round(completed / total * 100) if total else 100,
        tour_completed=progress.tour_completed_at is not None,
        dismissed_at=progress.dismissed_at,
        steps=steps,
    )


def update_onboarding(
    db: Session,
    current_user: User,
    payload: OnboardingUpdate,
) -> OnboardingRead:
    progress = _get_or_create_progress(db, current_user)
    completed = set(progress.completed_steps)
    if payload.completed_step:
        step = payload.completed_step.strip().upper()
        if step not in MANUAL_STEPS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El paso no admite confirmacion manual",
            )
        completed.add(step)
    if payload.tour_completed:
        completed.add("TOUR")
        progress.tour_completed_at = datetime.now(UTC)
    if payload.dismissed is not None:
        progress.dismissed_at = datetime.now(UTC) if payload.dismissed else None
    progress.completed_steps = sorted(completed)
    db.commit()
    return get_onboarding(db, current_user)


def restart_onboarding(db: Session, current_user: User) -> OnboardingRead:
    progress = _get_or_create_progress(db, current_user)
    progress.completed_steps = []
    progress.tour_completed_at = None
    progress.dismissed_at = None
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        "RESTART",
        "ONBOARDING",
        "Recorrido de primeros pasos reiniciado",
        progress.id,
    )
    db.commit()
    return get_onboarding(db, current_user)


def _get_or_create_progress(db: Session, current_user: User) -> OnboardingProgress:
    progress = db.scalar(
        select(OnboardingProgress).where(OnboardingProgress.user_id == current_user.id)
    )
    if progress:
        return progress
    progress = OnboardingProgress(
        company_id=current_user.company_id,
        user_id=current_user.id,
        completed_steps=[],
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def _count(db: Session, model, company_id) -> int:
    query = select(func.count()).select_from(model).where(model.company_id == company_id)
    return db.scalar(query) or 0


def _step(
    key: str,
    title: str,
    description: str,
    href: str,
    complete: bool,
    automatic: bool,
) -> OnboardingStepRead:
    return OnboardingStepRead(
        key=key,
        title=title,
        description=description,
        href=href,
        complete=complete,
        automatic=automatic,
    )
