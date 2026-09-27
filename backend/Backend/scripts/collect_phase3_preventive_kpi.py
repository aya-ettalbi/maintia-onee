from pathlib import Path
import subprocess
from datetime import datetime

backend = Path.cwd()
output = backend / "audit_phase3_preventive_kpi.txt"

files = [
    "app/core/enums.py",
    "app/models/maintenance.py",
    "app/models/equipment.py",
    "app/models/stock.py",
    "app/models/audit.py",
    "app/models/ai_core.py",
    "app/schemas/maintenance.py",
    "app/schemas/equipment.py",
    "app/api/routes/interventions.py",
    "app/api/routes/dashboard.py",
    "app/api/routes/recommendations.py",
    "app/api/routes/phase2_interventions.py",
    "app/services/phase2_interventions.py",
    "app/services/audit.py",
    "app/api/router.py",
]

tables = [
    "equipments",
    "maintenance_requests",
    "interventions",
    "intervention_status_history",
    "intervention_actions",
    "intervention_parts",
    "spare_parts",
    "stock_movements",
    "recommendations",
    "notifications",
    "audit_logs",
]

with output.open("w", encoding="utf-8") as writer:
    writer.write("AUDIT PHASE 3 - MAINTENANCE PREVENTIVE ET KPI\n")
    writer.write(f"Date : {datetime.now().isoformat()}\n")
    writer.write(f"Backend : {backend}\n")

    for relative in files:
        path = backend / relative

        writer.write("\n" + "=" * 100 + "\n")
        writer.write(f"FICHIER : {relative}\n")
        writer.write("=" * 100 + "\n")

        if path.exists():
            writer.write(path.read_text(encoding="utf-8-sig"))
        else:
            writer.write("[FICHIER ABSENT]\n")

    writer.write("\n" + "=" * 100 + "\n")
    writer.write("STRUCTURE POSTGRESQL\n")
    writer.write("=" * 100 + "\n")

    for table in tables:
        writer.write(f"\n===== TABLE : {table} =====\n")

        result = subprocess.run(
            [
                "docker",
                "exec",
                "maintenance_onee_db",
                "psql",
                "-U",
                "maintenance_app",
                "-d",
                "maintenance_onee",
                "-c",
                rf"\d+ {table}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        writer.write(result.stdout)
        writer.write(result.stderr)

    writer.write("\n===== ENUMS POSTGRESQL =====\n")

    result = subprocess.run(
        [
            "docker",
            "exec",
            "maintenance_onee_db",
            "psql",
            "-U",
            "maintenance_app",
            "-d",
            "maintenance_onee",
            "-c",
            """
SELECT
    t.typname AS enum_name,
    e.enumlabel AS enum_value
FROM pg_type t
JOIN pg_enum e ON e.enumtypid = t.oid
ORDER BY t.typname, e.enumsortorder;
""",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    writer.write(result.stdout)
    writer.write(result.stderr)

print(f"Audit cree : {output}")
