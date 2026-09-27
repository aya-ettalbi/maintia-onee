from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.privacy import normalize_for_matching


STOP_WORDS = {
    "a", "ai", "au", "aux", "avec", "ce", "ces", "comment", "dans",
    "de", "des", "du", "elle", "en", "est", "et", "faire", "il",
    "je", "la", "le", "les", "ma", "mes", "mon", "ne", "nous",
    "ou", "pas", "pour", "probleme", "que", "qui", "sur", "un",
    "une", "vous", "quelles", "quels", "sont",
}
EQUIPMENT_CODE_RE = re.compile(
    r"\b[A-Z]{2,5}[-_]?\d{3,}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedQuery:
    raw_query: str
    normalized_query: str
    intent: str
    classification_group: str | None
    equipment_code: str | None
    keywords: tuple[str, ...]


CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("IMPRIMANTE", (
        "imprimante", "impression", "papier", "bourrage", "toner",
        "cartouche", "developpeur", "photocop",
    )),
    ("SCANNER", ("scanner", "numerisation", "numeriser")),
    ("PC", (
        "ordinateur", "pc", "unite centrale", "maintenance uc",
        "ecran noir", "ram", "carte mere", "windows", "demarrage",
        "portable", "laptop",
    )),
    ("RESEAU", (
        "reseau", "connexion", "prise", "switch", "internet", "ip",
        "wifi", "ethernet",
    )),
    ("COMPTE", (
        "mot de passe", "compte", "sap", "solman", "isu",
        "messagerie", "login", "utilisateur bloque",
    )),
    ("SERVEUR", ("serveur", "unix", "linux")),
    ("VIDEO_PROJECTEUR", (
        "videoprojecteur", "projecteur", "projection",
    )),
)


def infer_intent(
    normalized: str,
    equipment_code: str | None,
) -> str:
    if (
        equipment_code
        and any(
            phrase in normalized
            for phrase in (
                "historique",
                "ancienne panne",
                "anciennes pannes",
                "pannes precedentes",
                "interventions precedentes",
            )
        )
    ):
        return "EQUIPMENT_HISTORY"

    if any(phrase in normalized for phrase in (
        "combien", "statistique", "plus frequent", "top ",
        "moyenne", "taux", "nombre de",
    )):
        return "ANALYTICS"

    if any(phrase in normalized for phrase in (
        "risque", "prevoir", "prediction", "prochaine panne",
        "critique",
    )):
        return "RISK"

    if any(phrase in normalized for phrase in (
        "stock", "piece", "rupture", "approvisionnement",
    )):
        return "STOCK"

    return "DIAGNOSTIC"


def infer_classification_group(normalized: str) -> str | None:
    best_group: str | None = None
    best_score = 0

    for group, terms in CATEGORY_RULES:
        score = sum(1 for term in terms if term in normalized)
        if score > best_score:
            best_score = score
            best_group = group

    return best_group


def extract_keywords(normalized: str) -> tuple[str, ...]:
    tokens = [
        token
        for token in normalized.split()
        if len(token) >= 3
        and token not in STOP_WORDS
        and not token.isdigit()
    ]
    return tuple(dict.fromkeys(tokens))


def parse_query(query: str) -> ParsedQuery:
    normalized = normalize_for_matching(query)
    code_match = EQUIPMENT_CODE_RE.search(query)

    equipment_code = (
        code_match.group(0).upper().replace("_", "-")
        if code_match
        else None
    )

    return ParsedQuery(
        raw_query=query,
        normalized_query=normalized,
        intent=infer_intent(normalized, equipment_code),
        classification_group=infer_classification_group(normalized),
        equipment_code=equipment_code,
        keywords=extract_keywords(normalized),
    )
