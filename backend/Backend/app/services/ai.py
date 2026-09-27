from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import RiskLevel
from app.models.equipment import Equipment
from app.models.maintenance import Intervention


def diagnostic_suggestions(db: Session, description: str, top_k: int) -> list[dict]:
    rows = db.execute(
        select(Intervention).where(
            Intervention.diagnosis.is_not(None),
            Intervention.solution.is_not(None),
        )
    ).scalars().all()

    if not rows:
        return []

    documents = [
        " ".join(filter(None, [row.diagnosis or "", row.solution or ""]))
        for row in rows
    ]

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="scikit-learn n'est pas installé",
        ) from exc

    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), max_features=10000)
    matrix = vectorizer.fit_transform([description, *documents])
    scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    best_indexes = scores.argsort()[::-1][:top_k]

    return [
        {
            "intervention_id": rows[index].id,
            "similarity": round(float(scores[index]), 4),
            "diagnosis": rows[index].diagnosis,
            "solution": rows[index].solution,
        }
        for index in best_indexes
        if scores[index] > 0
    ]


def equipment_risk_score(db: Session, equipment_id: int) -> dict:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Équipement introuvable")

    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=180)
    interventions = db.execute(
        select(Intervention).where(
            Intervention.equipment_id == equipment_id,
            Intervention.created_at >= six_months_ago,
        )
    ).scalars().all()

    score = 0.0
    factors: list[str] = []

    reference_date = equipment.commissioning_date or equipment.acquisition_date
    age_years = None
    if reference_date:
        age_years = max((date.today() - reference_date).days / 365.25, 0)
        if age_years >= 5:
            score += 20
            factors.append(f"Ancienneté élevée : {age_years:.1f} ans")
        elif age_years >= 3:
            score += 10
            factors.append(f"Ancienneté à surveiller : {age_years:.1f} ans")

    failure_count = len(interventions)
    if failure_count >= 4:
        score += 35
        factors.append(f"{failure_count} interventions sur les 6 derniers mois")
    elif failure_count >= 2:
        score += 20
        factors.append(f"{failure_count} interventions sur les 6 derniers mois")

    total_cost = sum((Decimal(i.actual_cost or 0) for i in interventions), Decimal("0"))
    if total_cost >= Decimal("10000"):
        score += 25
        factors.append(f"Coût récent élevé : {total_cost:.2f}")
    elif total_cost >= Decimal("5000"):
        score += 15
        factors.append(f"Coût récent important : {total_cost:.2f}")

    diagnosis_counts: dict[str, int] = {}
    for intervention in interventions:
        if intervention.diagnosis:
            key = intervention.diagnosis.strip().lower()
            diagnosis_counts[key] = diagnosis_counts.get(key, 0) + 1
    if diagnosis_counts and max(diagnosis_counts.values()) >= 2:
        score += 20
        factors.append("Panne ou diagnostic récurrent")

    score = min(score, 100.0)
    if score >= 70:
        level = RiskLevel.HIGH.value
        action = "Programmer une maintenance préventive prioritaire et étudier le renouvellement."
    elif score >= 40:
        level = RiskLevel.MEDIUM.value
        action = "Planifier un contrôle préventif et renforcer la surveillance."
    else:
        level = RiskLevel.LOW.value
        action = "Maintenir la surveillance normale et respecter le plan préventif."

    if not factors:
        factors.append("Aucun facteur de risque majeur détecté avec les données disponibles")

    return {
        "equipment_id": equipment_id,
        "score": round(score, 2),
        "level": level,
        "factors": factors,
        "recommended_action": action,
    }
