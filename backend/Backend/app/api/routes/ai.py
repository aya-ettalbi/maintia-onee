from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.intelligence import (
    DiagnosticRequest,
    DiagnosticSuggestion,
    RiskScoreResponse,
)
from app.services.ai import diagnostic_suggestions, equipment_risk_score


router = APIRouter(prefix="/ai", tags=["Intelligence artificielle"])


@router.post("/diagnostic-suggestions", response_model=list[DiagnosticSuggestion])
def suggest_diagnostics(
    payload: DiagnosticRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return diagnostic_suggestions(db, payload.description, payload.top_k)


@router.get("/equipments/{equipment_id}/risk-score", response_model=RiskScoreResponse)
def risk_score(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return equipment_risk_score(db, equipment_id)
