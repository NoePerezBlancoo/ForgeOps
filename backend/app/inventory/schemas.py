from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator

from app.core.enums import InventoryMovementType
from app.core.schemas import ORMModel, UserSummary


class InventoryItemCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=3000)
    stock: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=3)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=3)
    unit: str = Field(default="ud", min_length=1, max_length=24)
    location: str | None = Field(default=None, max_length=160)
    cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class InventoryItemUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    code: str | None = Field(default=None, min_length=2, max_length=60)
    name: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=3000)
    minimum_stock: Decimal | None = Field(default=None, ge=0, decimal_places=3)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    location: str | None = Field(default=None, max_length=160)
    cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class InventoryItemRead(ORMModel):
    id: UUID
    company_id: UUID
    code: str
    name: str
    description: str | None
    stock: Decimal
    minimum_stock: Decimal
    unit: str
    location: str | None
    cost: Decimal | None
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def low_stock(self) -> bool:
        return self.stock <= self.minimum_stock


class InventoryItemSummary(ORMModel):
    id: UUID
    code: str
    name: str
    unit: str


class StockMovementCreate(BaseModel):
    movement_type: InventoryMovementType
    quantity: Decimal = Field(decimal_places=3)
    reason: str = Field(min_length=4, max_length=255)
    expected_version: int = Field(ge=1)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("La cantidad no puede ser cero")
        return value


class InventoryMovementRead(ORMModel):
    id: UUID
    company_id: UUID
    item_id: UUID
    user_id: UUID
    work_order_id: UUID | None
    reversal_of_id: UUID | None
    movement_type: InventoryMovementType
    quantity: Decimal
    resulting_stock: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    reason: str
    created_at: datetime
    user: UserSummary
    item: InventoryItemSummary
