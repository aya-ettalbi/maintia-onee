from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    InterventionStatus,
    MaintenanceType,
    Priority,
    RequestStatus,
)


class MaintenanceRequestCreate(BaseModel):
    equipment_id: int
    description: str = Field(min_length=5)
    category: str | None = Field(default=None, max_length=150)
    priority: Priority = Priority.MEDIUM


class MaintenanceRequestUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=5)
    category: str | None = Field(default=None, max_length=150)
    priority: Priority | None = None
    assigned_technician_id: int | None = None


class MaintenanceRequestStatusChange(BaseModel):
    status: RequestStatus
    assigned_technician_id: int | None = None


class MaintenanceRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    equipment_id: int
    requester_id: int
    assigned_technician_id: int | None
    description: str
    category: str | None
    priority: str
    status: str
    submitted_at: datetime
    assigned_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InterventionCreate(BaseModel):
    request_id: int | None = None
    equipment_id: int
    technician_id: int
    maintenance_type: MaintenanceType = MaintenanceType.CORRECTIVE
    estimated_cost: Decimal = Decimal("0")


class InterventionUpdate(BaseModel):
    technician_id: int | None = None
    maintenance_type: MaintenanceType | None = None
    diagnosis: str | None = None
    solution: str | None = None
    estimated_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    test_result: str | None = None


class InterventionStatusChange(BaseModel):
    status: InterventionStatus
    comment: str | None = None


class InterventionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    request_id: int | None
    equipment_id: int
    technician_id: int
    maintenance_type: str
    diagnosis: str | None
    solution: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    estimated_cost: Decimal
    actual_cost: Decimal
    test_result: str | None
    closed_by_id: int | None
    created_at: datetime
    updated_at: datetime


class InterventionActionCreate(BaseModel):
    description: str = Field(min_length=3)


class InterventionActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    intervention_id: int
    description: str
    performed_by_id: int
    performed_at: datetime
    created_at: datetime


class InterventionStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    intervention_id: int
    old_status: str | None
    new_status: str
    changed_by_id: int
    comment: str | None
    changed_at: datetime


class InterventionPartCreate(BaseModel):
    part_id: int
    quantity: int = Field(gt=0)


class InterventionPartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    intervention_id: int
    part_id: int
    quantity: int
    unit_price: Decimal
    created_at: datetime
