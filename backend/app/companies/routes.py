from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.companies.models import Company
from app.companies.schemas import CompanyRead
from app.users.models import User

router = APIRouter(prefix="/companies", tags=["Empresas"])


@router.get("/current", response_model=CompanyRead)
def current_company(current_user: User = Depends(get_current_user)) -> Company:
    return current_user.company
