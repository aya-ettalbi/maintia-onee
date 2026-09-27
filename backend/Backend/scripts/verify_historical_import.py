from sqlalchemy import func, inspect, select, text

from app.db.session import SessionLocal, engine
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
    print("=" * 72)
    print("VERIFICATION DE L'IMPORT HISTORIQUE ONEE")
    print("=" * 72)

    with engine.connect() as connection:
        print("Connexion PostgreSQL :", connection.execute(text("SELECT 1")).scalar())

    tables = set(inspect(engine).get_table_names())

    with SessionLocal() as db:
        total = 0
        for model in MODELS:
            name = model.__tablename__
            if name not in tables:
                print(f"[MANQUANTE] {name}")
                continue

            count = db.scalar(select(func.count()).select_from(model)) or 0
            total += count
            print(f"[OK] {name:<36} {count:>8} lignes")

        print("-" * 72)
        print(f"TOTAL HISTORIQUE : {total} lignes")


if __name__ == "__main__":
    main()
