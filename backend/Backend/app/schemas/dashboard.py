from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_equipments: int
    equipments_in_service: int
    equipments_in_failure: int
    open_requests: int
    active_interventions: int
    low_stock_parts: int
    open_recommendations: int
    average_repair_hours: float | None
