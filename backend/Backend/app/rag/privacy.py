from __future__ import annotations

import re
import unicodedata


EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
MAC_RE = re.compile(
    r"\b(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}\b",
    re.IGNORECASE,
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?212[\s.-]?)?(?:0)?[5-7]\d(?:[\s.-]?\d{2}){4}(?!\d)"
)
SERIAL_RE = re.compile(
    r"(?i)\b(?:S\s*/?\s*N|N[°º]?\s*S[ÉE]RIE|NUM[ÉE]RO\s+DE\s+S[ÉE]RIE)"
    r"\s*[:=-]?\s*[A-Z0-9._/-]{5,}\b"
)
MATRICULE_RE = re.compile(
    r"(?i)\bMATRICULE\s*[:=-]?\s*[A-Z0-9._/-]{3,}\b"
)
PASSWORD_VALUE_RE = re.compile(
    r"(?ix)"
    r"\b(?:MOT\s+DE\s+PASSE|PASSWORD|MDP)"
    r"(?:\s+(?:INITIAL|INITIALE|TEMPORAIRE|PROVISOIRE|NOUVEAU|NOUVELLE))?"
    r"\s*(?:[:=]|EST|INITIALIS[ÉE]?\s+PAR|R[ÉE]INITIALIS[ÉE]?\s+[ÀA])"
    r"\s*[^\s,;.]{3,}"
)
SAP_ACCOUNT_RE = re.compile(
    r"(?i)\b(?:COMPTE\s+)?(?:SAP(?:-[A-Z0-9]+)?|SOLMAN|ISU)"
    r"\s*[:=-]\s*[A-Z0-9._/-]{2,}"
)
PERSON_TITLE_RE = re.compile(
    r"(?i)\b(?:M\.|MR|MME|MONSIEUR|MADAME|MELLE)"
    r"\s+[A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý'’-]+"
    r"(?:\s+[A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý'’-]+)?"
)
AGENT_NAME_RE = re.compile(
    r"(?i)\b(?:AGENT|UTILISATEUR|B[ÉE]N[ÉE]FICIAIRE|DEMANDEUR)"
    r"\s*[:=-]\s*[A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý'’-]+"
    r"(?:\s+[A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý'’-]+)?"
)

def compact_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def anonymize_text(value: object) -> str:
    """
    Nettoyage défensif avant indexation et avant appel à OpenRouter.

    Le texte technique reste exploitable, mais les secrets et identifiants
    personnels sont remplacés par des marqueurs explicites.
    """
    text = compact_spaces(value)
    if not text:
        return ""

    substitutions = (
        (EMAIL_RE, "[EMAIL]"),
        (MAC_RE, "[MAC]"),
        (IP_RE, "[ADRESSE_IP]"),
        (PHONE_RE, "[TELEPHONE]"),
        (SERIAL_RE, "S/N: [NUMERO_SERIE]"),
        (MATRICULE_RE, "MATRICULE: [MATRICULE]"),
        (PASSWORD_VALUE_RE, "MOT DE PASSE: [SECRET_SUPPRIME]"),
        (SAP_ACCOUNT_RE, "COMPTE: [COMPTE_INTERNE]"),
        (PERSON_TITLE_RE, "[UTILISATEUR]"),
        (AGENT_NAME_RE, "UTILISATEUR: [UTILISATEUR]"),
    )

    for pattern, replacement in substitutions:
        text = pattern.sub(replacement, text)

    # Deuxième passage pour des formes résiduelles du type "MDP initial : 123456".
    text = re.sub(
        r"(?i)\b(?:MDP|PASSWORD|MOT\s+DE\s+PASSE)"
        r"(?:\s+(?:INITIAL|INITIALE|TEMPORAIRE|PROVISOIRE))?"
        r"\s*[:=-]?\s*\d{4,12}\b",
        "MOT DE PASSE: [SECRET_SUPPRIME]",
        text,
    )

    # Identifiants numériques très longs.
    text = re.sub(
        r"(?<!\d)\d{8,}(?!\d)",
        "[IDENTIFIANT_NUMERIQUE]",
        text,
    )

    return compact_spaces(text)


def normalize_for_matching(value: object) -> str:
    text = strip_accents(compact_spaces(value)).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return compact_spaces(text)
