from app.models.phase4_failure_forecast import (
    FailureForecast,
    FailureForecastRun,
)
from app.models.phase3_preventive import (
    GeneratedMaintenanceReport,
    PreventiveMaintenanceExecution,
    PreventiveMaintenancePlan,
)
from app.models.ai_core import (
    EquipmentHistoricalLink,
    RagSyncQueue,
)
from app.models.audit import AuditLog, Notification
from app.models.equipment import Equipment, EquipmentAssignment, EquipmentCategory
from app.models.intelligence import Recommendation
from app.models.maintenance import (
    Intervention,
    InterventionAction,
    InterventionStatusHistory,
    MaintenanceRequest,
)
from app.models.organization import Location, Service
from app.models.stock import InterventionPart, SparePart, StockMovement
from app.models.user import User

__all__ = [
    "AuditLog",
    "Notification",
    "Equipment",
    "EquipmentAssignment",
    "EquipmentCategory",
    "Recommendation",
    "Intervention",
    "InterventionAction",
    "InterventionStatusHistory",
    "MaintenanceRequest",
    "Location",
    "Service",
    "InterventionPart",
    "SparePart",
    "StockMovement",
    "User",
    "EquipmentHistoricalLink",
    "RagSyncQueue",
    "GeneratedMaintenanceReport",
    "PreventiveMaintenanceExecution",
    "PreventiveMaintenancePlan",
    "FailureForecast",
    "FailureForecastRun",
]
