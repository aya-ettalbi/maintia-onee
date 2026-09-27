from __future__ import annotations

from app.rag.privacy import anonymize_text


TESTS = [
    "Le MDP initial : 123456",
    "Le mot de passe initial 123456",
    "Mot de passe initialisé par 123456.",
    "Compte SAP: akorichi, email aya@example.com",
    "Mr SABBAR Ahmed, MAC 10-60-4B-79-C3-49",
    "S/N : TRF32903N9, matricule: 12345678",
]


def main() -> None:
    for value in TESTS:
        print("=" * 70)
        print("AVANT :", value)
        print("APRÈS :", anonymize_text(value))


if __name__ == "__main__":
    main()
