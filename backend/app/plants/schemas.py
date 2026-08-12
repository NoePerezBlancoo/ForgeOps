from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import ORMModel


class PlantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=40)
    address: str | None = Field(default=None, max_length=1000)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "code", "address", "description")
    @classmethod
    def strip_values(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class PlantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    address: str | None = Field(default=None, max_length=1000)
    description: str | None = Field(default=None, max_length=2000)
    active: bool | None = None

    @field_validator("name", "code", "address", "description")
    @classmethod
    def strip_values(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class PlantRead(ORMModel):
    id: UUID
    company_id: UUID
    name: str
    code: str
    address: str | None
    description: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
