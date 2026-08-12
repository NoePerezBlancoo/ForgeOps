from datetime import datetime
from uuid import UUID

from app.core.enums import UserRole
from app.core.schemas import ORMModel


class CompanySummary(ORMModel):
    id: UUID
    name: str


class UserRead(ORMModel):
    id: UUID
    company_id: UUID
    full_name: str
    email: str
    role: UserRole
    active: bool
    created_at: datetime
    company: CompanySummary


class UserOption(ORMModel):
    id: UUID
    full_name: str
    email: str
    role: UserRole
