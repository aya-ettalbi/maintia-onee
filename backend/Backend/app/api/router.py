from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    ai,
    audit,
    auth,
    chat,
    dashboard,
    equipments,
    interventions,
    maintenance_requests,
    notifications,
    organization,
    recommendations,
    stock,
    system,
    users,
)
from app.api.routes.historical import (
    router as historical_router,
)


api_router = APIRouter()

api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(organization.router)
api_router.include_router(equipments.router)
api_router.include_router(maintenance_requests.router)
api_router.include_router(interventions.router)
api_router.include_router(stock.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
api_router.include_router(recommendations.router)
api_router.include_router(notifications.router)
api_router.include_router(audit.router)
api_router.include_router(historical_router)
api_router.include_router(chat.router)

from app.api.routes.backend_completion import router as backend_completion_router
api_router.include_router(backend_completion_router)

from app.api.routes.phase2_interventions import router as phase2_interventions_router
api_router.include_router(phase2_interventions_router)

from app.api.routes.phase3_preventive_kpi import router as phase3_preventive_kpi_router
api_router.include_router(phase3_preventive_kpi_router)

from app.api.routes.phase4_failure_forecast import router as phase4_failure_forecast_router
api_router.include_router(phase4_failure_forecast_router)
