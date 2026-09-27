from __future__ import annotations

from app.rag.privacy import anonymize_text


TESTS = [
    (
        "Email aya@example.com et MAC 10-60-4B-79-C3-49.",
        "données de contact et MAC",
    ),
    (
        "Mr SABBAR Ahmed utilise le compte SAP: akorichi.",
        "nom et compte interne",
    ),
    (
        "Mot de passe initialisé par 123456.",
        "secret temporaire",
    ),
    (
        "S/N : TRF32903N9, matricule: 12345678.",
        "numéro de série et matricule",
    ),
]


def main() -> None:
    for text, label in TESTS:
        print("=" * 60)
        print("TEST :", label)
        print("AVANT :", text)
        print("APRÈS :", anonymize_text(text))


if __name__ == "__main__":
    main()
