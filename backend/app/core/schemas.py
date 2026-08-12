from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
    sort: str
    filters: dict[str, str | bool]


class UserSummary(ORMModel):
    id: UUID
    full_name: str
    email: str


class PlantSummary(ORMModel):
    id: UUID
    name: str
    code: str


class AssetSummary(ORMModel):
    id: UUID
    code: str
    name: str


class AuditFields(ORMModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
