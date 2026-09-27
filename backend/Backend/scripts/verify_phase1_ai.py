from sqlalchemy import text

from app.db.session import engine


QUERIES = {
    "equipment_categories": "SELECT COUNT(*) FROM equipment_categories",
    "equipments": "SELECT COUNT(*) FROM equipments",
    "historical_requests": "SELECT COUNT(*) FROM historical_requests",
    "equipment_historical_links": (
        "SELECT COUNT(*) FROM equipment_historical_links"
    ),
    "rag_sync_queue": "SELECT COUNT(*) FROM rag_sync_queue",
}


def main() -> None:
    with engine.connect() as connection:
        print("Base :", connection.execute(
            text("SELECT current_database()")
        ).scalar())
        print("Utilisateur :", connection.execute(
            text("SELECT current_user")
        ).scalar())
        print()

        for label, query in QUERIES.items():
            value = connection.execute(text(query)).scalar()
            print(f"{label}: {value}")

        print("\nMéthodes de jointure :")
        rows = connection.execute(
            text(
                """
                SELECT link_method, COUNT(*)
                FROM equipment_historical_links
                GROUP BY link_method
                ORDER BY COUNT(*) DESC
                """
            )
        ).all()

        for method, count in rows:
            print(f"- {method}: {count}")


if __name__ == "__main__":
    main()
