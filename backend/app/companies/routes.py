from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.companies.models import Company
from app.companies.schemas import CompanyModulesUpdate, CompanyRead, CompanyUpdate
from app.companies.service import update_company, update_company_modules
from app.core.database import get_db
from app.core.enums import UserRole
from app.users.models import User

router = APIRouter(prefix="/companies", tags=["Empresas"])
administrators = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)


@router.get("/current", response_model=CompanyRead)
def current_company(current_user: User = Depends(get_current_user)) -> Company:
    return current_user.company


@router.patch("/current", response_model=CompanyRead)
def update_current_company(
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
) -> Company:
    return update_company(db, current_user, payload)


@router.patch("/current/modules", response_model=CompanyRead)
def update_current_modules(
    payload: CompanyModulesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
) -> Company:
    return update_company_modules(db, current_user, payload)
