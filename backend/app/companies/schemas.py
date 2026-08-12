from datetime import datetime
from uuid import UUID

from app.core.schemas import ORMModel


class CompanyRead(ORMModel):
    id: UUID
    name: str
    tax_id: str
    address: str | None
    phone: str | None
    email: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
