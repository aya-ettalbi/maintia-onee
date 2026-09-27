from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InterventionActionUpdate(BaseModel):
    description: str = Field(min_length=3, max_length=4000)


class InterventionPartUpdate(BaseModel):
    quantity: int = Field(gt=0, le=100000)


class InterventionCloseRequest(BaseModel):
    diagnosis: str = Field(min_length=3, max_length=10000)
    solution: str = Field(min_length=3, max_length=10000)
    test_result: str = Field(min_length=2, max_length=5000)
    comment: str | None = Field(default=None, max_length=2000)


class InterventionCancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class StockSummaryResponse(BaseModel):
    total_parts: int
    active_parts: int
    total_quantity: int
    low_stock_parts: int
    out_of_stock_parts: int
    inventory_value: Decimal


class StockAlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    part_id: int
    code: str
    name: str
    quantity: int
    minimum_threshold: int
    shortage: int
    suggested_order_quantity: int
    risk: str


class StockAlertsResponse(BaseModel):
    total: int
    items: list[StockAlertItem]
