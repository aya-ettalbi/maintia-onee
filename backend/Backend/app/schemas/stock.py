from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import StockMovementType


class SparePartCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    category: str | None = Field(default=None, max_length=150)
    quantity: int = Field(default=0, ge=0)
    minimum_threshold: int = Field(default=0, ge=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    supplier: str | None = Field(default=None, max_length=255)


class SparePartUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    category: str | None = Field(default=None, max_length=150)
    minimum_threshold: int | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=255)
    active: bool | None = None


class SparePartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category: str | None
    quantity: int
    minimum_threshold: int
    unit_price: Decimal
    supplier: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class StockMovementCreate(BaseModel):
    part_id: int
    movement_type: StockMovementType
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    intervention_id: int | None = None
    reason: str | None = None


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    movement_type: str
    quantity: int
    unit_cost: Decimal
    intervention_id: int | None
    performed_by_id: int
    reason: str | None
    created_at: datetime
