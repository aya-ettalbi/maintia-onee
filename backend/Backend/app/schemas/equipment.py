from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import EquipmentStatus


class EquipmentCategoryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None


class EquipmentCategoryUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=50)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None


class EquipmentCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class EquipmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100)
    category_id: int
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=150)
    acquisition_date: date | None = None
    commissioning_date: date | None = None
    status: EquipmentStatus = EquipmentStatus.IN_SERVICE
    location_id: int | None = None
    current_service_id: int | None = None
    warranty_end_date: date | None = None
    notes: str | None = None


class EquipmentUpdate(BaseModel):
    category_id: int | None = None
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=150)
    acquisition_date: date | None = None
    commissioning_date: date | None = None
    status: EquipmentStatus | None = None
    location_id: int | None = None
    current_service_id: int | None = None
    warranty_end_date: date | None = None
    notes: str | None = None


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    category_id: int
    brand: str | None
    model: str | None
    serial_number: str | None
    acquisition_date: date | None
    commissioning_date: date | None
    status: str
    location_id: int | None
    current_service_id: int | None
    warranty_end_date: date | None
    notes: str | None
    archived: bool
    created_at: datetime
    updated_at: datetime


class EquipmentAssignmentCreate(BaseModel):
    user_id: int | None = None
    service_id: int | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        if self.user_id is None and self.service_id is None:
            raise ValueError("user_id ou service_id est obligatoire")
        return self


class EquipmentAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    user_id: int | None
    service_id: int | None
    assigned_at: datetime
    returned_at: datetime | None
    is_active: bool
    comment: str | None
    created_at: datetime
