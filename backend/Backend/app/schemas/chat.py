from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=5,
        max_length=2000,
    )
    candidate_k: int = Field(
        default=15,
        ge=10,
        le=60,
    )
    top_k: int = Field(
        default=4,
        ge=3,
        le=10,
    )


class ChatSource(BaseModel):
    reference: str | None = None
    final_score: float
    reranker_score: float
    dense_score: float
    classification: str | None = None
    equipment_code: str | None = None
    equipment_brand: str | None = None
    equipment_model: str | None = None
    link_trust: str | None = None


class LLMRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    probable_causes: list[str]
    recommended_checks: list[str]
    historical_solutions: list[str]
    warnings: list[str]


class ChatResponse(BaseModel):
    answer: str
    summary: str
    probable_causes: list[str]
    recommended_checks: list[str]
    historical_solutions: list[str]
    warnings: list[str]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    confidence_score: int = Field(ge=0, le=100)
    human_validation_required: bool = True
    intent: str
    classification_group: str | None = None
    equipment_code: str | None = None
    model: str
    llm_used: bool
    sources: list[ChatSource]
