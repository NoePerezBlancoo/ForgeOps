from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.enums import AssetStatus, Criticality
from app.core.schemas import ORMModel, PlantSummary


class AssetBase(BaseModel):
    plant_id: UUID
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    installation_date: date | None = None
    status: AssetStatus = AssetStatus.ACTIVE
    criticality: Criticality = Criticality.MEDIUM
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    plant_id: UUID | None = None
    code: str | None = Field(default=None, min_length=2, max_length=50)
    name: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    installation_date: date | None = None
    status: AssetStatus | None = None
    criticality: Criticality | None = None
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class AssetRead(ORMModel):
    id: UUID
    company_id: UUID
    plant_id: UUID
    code: str
    name: str
    description: str | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    installation_date: date | None
    status: AssetStatus
    criticality: Criticality
    location: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    plant: PlantSummary
