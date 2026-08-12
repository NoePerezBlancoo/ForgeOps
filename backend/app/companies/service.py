
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import add_audit_event
from app.companies.entitlements import (
    company_usage,
    effective_limits,
    effective_modules,
    feature_enabled,
    normalize_modules,
)
from app.companies.models import Company
from app.companies.schemas import CompanyEntitlementsRead, CompanyModulesUpdate, CompanyUpdate
from app.users.models import User


def update_company(db: Session, current_user: User, payload: CompanyUpdate) -> Company:
    company = current_user.company
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(company, field, value)
    add_audit_event(
        db,
        company.id,
        current_user.id,
        "UPDATE",
        "COMPANY",
        f"Configuracion de {company.name} actualizada",
        company.id,
        {"fields": sorted(changes)},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El identificador fiscal ya pertenece a otra empresa",
        ) from exc
    db.refresh(company)
    return company


def update_company_modules(
    db: Session,
    current_user: User,
    payload: CompanyModulesUpdate,
) -> Company:
    company = current_user.company
    previous = set(company.enabled_modules)
    normalized = normalize_modules(company.plan, payload.enabled_modules)
    requested = {module.value for module in payload.enabled_modules}
    if set(normalized) != requested:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El plan actual no permite activar todos los modulos solicitados",
        )
    company.enabled_modules = normalized
    add_audit_event(
        db,
        company.id,
        current_user.id,
        "UPDATE",
        "MODULES",
        "Modulos operativos actualizados",
        company.id,
        {
            "enabled": company.enabled_modules,
            "disabled": sorted(previous - set(company.enabled_modules)),
        },
    )
    db.commit()
    db.refresh(company)
    return company


def get_company_entitlements(db: Session, company: Company) -> CompanyEntitlementsRead:
    known_features = (
        "PWA",
        "AUDIT",
        "EXPORT",
        "DOCUMENT_AI",
        "INDUSTRIAL_INTEGRATIONS",
        "SSO",
    )
    return CompanyEntitlementsRead(
        plan=company.plan,
        modules=effective_modules(company),
        limits=effective_limits(company),
        usage=company_usage(db, company.id),
        features={feature: feature_enabled(company, feature) for feature in known_features},
    )
