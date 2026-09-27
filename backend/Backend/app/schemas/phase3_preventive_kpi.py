from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import Priority


class PreventivePlanCreate(BaseModel):
    equipment_id: int
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    frequency_days: int = Field(ge=1, le=3650)
    priority: Priority = Priority.MEDIUM
    assigned_technician_id: int | None = None
    next_due_date: date


class PreventivePlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    frequency_days: int | None = Field(default=None, ge=1, le=3650)
    priority: Priority | None = None
    assigned_technician_id: int | None = None
    next_due_date: date | None = None


class PreventivePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    title: str
    description: str | None
    frequency_days: int
    priority: str
    assigned_technician_id: int | None
    active: bool
    next_due_date: date
    last_executed_at: datetime | None
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class PreventiveExecutionCreate(BaseModel):
    technician_id: int | None = None
    estimated_cost: float = Field(default=0, ge=0)
    notes: str | None = Field(default=None, max_length=3000)


class PreventiveExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    intervention_id: int
    scheduled_date: date
    triggered_at: datetime
    status: str
    notes: str | None
    triggered_by_id: int
    created_at: datetime
    updated_at: datetime


class MaintenanceKpiResponse(BaseModel):
    period_start: date
    period_end: date
    total_interventions: int
    completed_interventions: int
    corrective_interventions: int
    preventive_interventions: int
    preventive_ratio_percent: float
    mttr_hours: float | None
    mtbf_hours: float | None
    estimated_availability_percent: float | None
    total_actual_cost: float
    active_preventive_plans: int
    due_preventive_plans: int
    overdue_preventive_plans: int


class EquipmentKpiResponse(BaseModel):
    equipment_id: int
    equipment_code: str
    total_interventions: int
    completed_interventions: int
    corrective_interventions: int
    preventive_interventions: int
    mttr_hours: float | None
    mtbf_hours: float | None
    total_actual_cost: float
    last_intervention_at: datetime | None
    next_preventive_due_date: date | None
    active_preventive_plans: int


class MonthlyReportMetrics(BaseModel):
    year: int
    month: int
    period_start: date
    period_end: date
    submitted_requests: int
    resolved_requests: int
    created_interventions: int
    completed_interventions: int
    corrective_interventions: int
    preventive_interventions: int
    mttr_hours: float | None
    total_actual_cost: float
    current_equipment_failures: int
    current_low_stock_parts: int
    due_preventive_plans: int
    overdue_preventive_plans: int


class MonthlyReportResponse(BaseModel):
    metrics: MonthlyReportMetrics
    summary: str
    llm_used: bool
    model_name: str | None = None


class GeneratedReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_type: str
    period_start: date
    period_end: date
    metrics: dict[str, Any]
    summary: str
    llm_used: bool
    model_name: str | None
    generated_by_id: int
    created_at: datetime
    updated_at: datetime
