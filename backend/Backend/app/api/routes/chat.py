from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.audit import log_action
from app.services.rag_chat import answer_with_rag


router = APIRouter(
    prefix="/chat",
    tags=["Chatbot IA"],
)


@router.post(
    "",
    response_model=ChatResponse,
)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    try:
        response = await answer_with_rag(
            message=payload.message,
            candidate_k=payload.candidate_k,
            top_k=payload.top_k,
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Le service IA est temporairement indisponible. "
                "Vérifiez Qdrant, les modèles locaux et la configuration "
                "OpenRouter."
            ),
        ) from error

    # Le texte de la question n'est pas stocké dans l'audit.
    log_action(
        db,
        actor_id=current_user.id,
        action="AI_CHAT",
        entity_type="RagChat",
        entity_id=None,
        details={
            "intent": response.intent,
            "classification_group": (
                response.classification_group
            ),
            "equipment_code": response.equipment_code,
            "confidence": response.confidence,
            "confidence_score": response.confidence_score,
            "llm_used": response.llm_used,
            "model": response.model,
            "source_references": [
                source.reference
                for source in response.sources
                if source.reference
            ],
        },
    )
    db.commit()

    return response
