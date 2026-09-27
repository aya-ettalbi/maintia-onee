from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import inspect


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import engine
from app.main import app


EXPECTED_OPERATIONS = {
    ("GET", "/api/v1/preventive-maintenance/plans"),
    ("POST", "/api/v1/preventive-maintenance/plans"),
    ("GET", "/api/v1/preventive-maintenance/plans/{plan_id}"),
    ("PATCH", "/api/v1/preventive-maintenance/plans/{plan_id}"),
    ("POST", "/api/v1/preventive-maintenance/plans/{plan_id}/activate"),
    ("POST", "/api/v1/preventive-maintenance/plans/{plan_id}/deactivate"),
    ("GET", "/api/v1/preventive-maintenance/due"),
    ("POST", "/api/v1/preventive-maintenance/plans/{plan_id}/execute"),
    ("GET", "/api/v1/preventive-maintenance/executions"),
    ("GET", "/api/v1/kpi/maintenance"),
    ("GET", "/api/v1/kpi/equipments/{equipment_id}"),
    ("GET", "/api/v1/reports/monthly"),
    ("POST", "/api/v1/reports/monthly/generate"),
    ("GET", "/api/v1/reports"),
}

EXPECTED_TABLES = {
    "preventive_maintenance_plans",
    "preventive_maintenance_executions",
    "generated_maintenance_reports",
}


def main() -> None:
    openapi = app.openapi()
    existing: set[tuple[str, str]] = set()

    for path, item in openapi.get("paths", {}).items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method in item:
                existing.add((method.upper(), path))

    missing_operations = sorted(EXPECTED_OPERATIONS - existing)
    tables = set(inspect(engine).get_table_names())
    missing_tables = sorted(EXPECTED_TABLES - tables)

    print("Chemins OpenAPI :", len(openapi.get("paths", {})))
    print("Operations Phase 3 attendues :", len(EXPECTED_OPERATIONS))
    print(
        "Operations Phase 3 presentes :",
        len(EXPECTED_OPERATIONS) - len(missing_operations),
    )
    print(
        "Tables Phase 3 presentes :",
        len(EXPECTED_TABLES) - len(missing_tables),
        "/",
        len(EXPECTED_TABLES),
    )

    if missing_operations:
        print("Operations manquantes :")
        for method, path in missing_operations:
            print("-", method, path)

    if missing_tables:
        print("Tables manquantes :")
        for table in missing_tables:
            print("-", table)

    if missing_operations or missing_tables:
        raise SystemExit(1)

    print("Phase 3 Preventif, KPI et Rapports : OK")


if __name__ == "__main__":
    main()
