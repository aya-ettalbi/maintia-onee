from sqlalchemy import inspect, text

from app.db.session import engine
from app.models.historical import (
    HistoricalITSupply,
    HistoricalOfficeSupply,
    HistoricalRequest,
    HistoricalSecurityIncident,
    HistoricalTask,
)


MODELS = [
    HistoricalRequest,
    HistoricalTask,
    HistoricalITSupply,
    HistoricalOfficeSupply,
    HistoricalSecurityIncident,
]


def main() -> None:
    print("Test de connexion PostgreSQL...")
    with engine.connect() as connection:
        value = connection.execute(text("SELECT 1")).scalar()
        if value != 1:
            raise RuntimeError("Le test SELECT 1 a échoué.")

    print("Connexion PostgreSQL : OK")
    print("Création des tables historiques...")

    for model in MODELS:
        model.__table__.create(bind=engine, checkfirst=True)
        print(f"  [OK] {model.__tablename__}")

    tables = set(inspect(engine).get_table_names())
    missing = {model.__tablename__ for model in MODELS} - tables

    if missing:
        raise RuntimeError("Tables manquantes : " + ", ".join(sorted(missing)))

    print("Toutes les tables historiques sont prêtes.")


if __name__ == "__main__":
    main()
