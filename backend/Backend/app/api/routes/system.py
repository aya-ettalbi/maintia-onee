from datetime import datetime, timezone

from fastapi import APIRouter


router = APIRouter(prefix="/system", tags=["Système"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "maintenance-intelligente-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
