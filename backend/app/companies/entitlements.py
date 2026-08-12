import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.companies.models import Company
from app.core.config import settings
from app.core.enums import CompanyModule, CompanyPlan
from app.documents.models import TechnicalDocument
from app.plants.models import Plant
from app.users.models import User


@dataclass(frozen=True)
class PlanPolicy:
    modules: frozenset[CompanyModule]
    limits: dict[str, int | None]
    features: frozenset[str]


ALL_MODULES = frozenset(CompanyModule)
STANDARD_FEATURES = frozenset({"PWA", "AUDIT", "EXPORT"})
AI_FEATURES = STANDARD_FEATURES | {"DOCUMENT_AI"}

PLAN_POLICIES = {
    CompanyPlan.DEMO: PlanPolicy(
        ALL_MODULES,
        {"users": 5, "plants": 1, "assets": 50, "storage_bytes": 250_000_000},
        AI_FEATURES,
    ),
    CompanyPlan.TRIAL: PlanPolicy(
        ALL_MODULES,
        {"users": 10, "plants": 2, "assets": 100, "storage_bytes": 500_000_000},
        AI_FEATURES,
    ),
    CompanyPlan.STARTER: PlanPolicy(
        frozenset({CompanyModule.PREVENTIVE, CompanyModule.DOCUMENTS}),
        {"users": 10, "plants": 2, "assets": 250, "storage_bytes": 2_000_000_000},
        STANDARD_FEATURES,
    ),
    CompanyPlan.PRO: PlanPolicy(
        ALL_MODULES,
        {"users": 40, "plants": 10, "assets": 2_500, "storage_bytes": 20_000_000_000},
        AI_FEATURES,
    ),
    CompanyPlan.INDUSTRIAL: PlanPolicy(
        ALL_MODULES,
        {
            "users": 150,
            "plants": 50,
            "assets": 10_000,
            "storage_bytes": 100_000_000_000,
        },
        AI_FEATURES | {"INDUSTRIAL_INTEGRATIONS"},
    ),
    CompanyPlan.ENTERPRISE: PlanPolicy(
        ALL_MODULES,
        {"users": None, "plants": None, "assets": None, "storage_bytes": None},
        AI_FEATURES | {"INDUSTRIAL_INTEGRATIONS", "SSO", "CUSTOM_RETENTION"},
    ),
    CompanyPlan.PROFESSIONAL: PlanPolicy(
        ALL_MODULES,
        {"users": 40, "plants": 10, "assets": 2_500, "storage_bytes": 20_000_000_000},
        AI_FEATURES,
    ),
}

LIMIT_KEYS = frozenset({"users", "plants", "assets", "storage_bytes"})


def policy_for(plan: CompanyPlan) -> PlanPolicy:
    return PLAN_POLICIES[plan]


def effective_modules(company: Company) -> list[CompanyModule]:
    selected = set(company.enabled_modules or [])
    allowed = policy_for(company.plan).modules
    return [module for module in CompanyModule if module.value in selected and module in allowed]


def normalize_modules(plan: CompanyPlan, modules: list[CompanyModule] | list[str]) -> list[str]:
    requested = {
        module.value if isinstance(module, CompanyModule) else module for module in modules
    }
    allowed = policy_for(plan).modules
    selected = {module for module in allowed if module.value in requested}
    if CompanyModule.KNOWLEDGE in selected:
        selected.add(CompanyModule.DOCUMENTS)
    return [module.value for module in CompanyModule if module in selected]


def module_enabled(company: Company, module: CompanyModule) -> bool:
    return module in effective_modules(company)


def effective_limits(company: Company) -> dict[str, int | None]:
    limits = dict(policy_for(company.plan).limits)
    for key, value in (company.limit_overrides or {}).items():
        if key in LIMIT_KEYS and (value is None or isinstance(value, int) and value >= 0):
            limits[key] = value
    return limits


def feature_enabled(company: Company, feature: str) -> bool:
    key = feature.strip().upper()
    override = (company.feature_overrides or {}).get(key)
    if isinstance(override, bool):
        return override
    if settings.feature_flags and key not in settings.feature_flags:
        return False
    return key in policy_for(company.plan).features


def company_usage(db: Session, company_id: uuid.UUID) -> dict[str, int]:
    return {
        "users": db.scalar(
            select(func.count(User.id)).where(
                User.company_id == company_id, User.active.is_(True)
            )
        )
        or 0,
        "plants": db.scalar(
            select(func.count(Plant.id)).where(
                Plant.company_id == company_id, Plant.active.is_(True)
            )
        )
        or 0,
        "assets": db.scalar(
            select(func.count(Asset.id)).where(Asset.company_id == company_id)
        )
        or 0,
        "storage_bytes": db.scalar(
            select(func.coalesce(func.sum(TechnicalDocument.file_size), 0)).where(
                TechnicalDocument.company_id == company_id
            )
        )
        or 0,
    }


def enforce_limit(
    db: Session,
    company: Company,
    resource: str,
    increment: int = 1,
) -> None:
    limit = effective_limits(company).get(resource)
    if limit is None:
        return
    usage = company_usage(db, company.id)[resource]
    if usage + increment > limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Se ha alcanzado el limite de {resource} del plan {company.plan.value}",
        )
