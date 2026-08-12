from uuid import UUID

from app.core.schemas import ORMModel


class PlantRead(ORMModel):
    id: UUID
    company_id: UUID
    name: str
    code: str
    address: str | None
    description: str | None
    active: bool
