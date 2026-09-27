from __future__ import annotations

from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


EXPECTED = {
    ("PATCH", "/api/v1/interventions/{intervention_id}/actions/{action_id}"),
    ("DELETE", "/api/v1/interventions/{intervention_id}/actions/{action_id}"),
    ("PATCH", "/api/v1/interventions/{intervention_id}/parts/{link_id}"),
    ("DELETE", "/api/v1/interventions/{intervention_id}/parts/{link_id}"),
    ("POST", "/api/v1/interventions/{intervention_id}/close"),
    ("POST", "/api/v1/interventions/{intervention_id}/cancel"),
    ("GET", "/api/v1/stock/summary"),
    ("GET", "/api/v1/stock/alerts"),
}


def main() -> None:
    openapi = app.openapi()
    existing: set[tuple[str, str]] = set()

    for path, item in openapi.get("paths", {}).items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method in item:
                existing.add((method.upper(), path))

    missing = sorted(EXPECTED - existing)

    print("Chemins OpenAPI :", len(openapi.get("paths", {})))
    print("Operations Phase 2 attendues :", len(EXPECTED))
    print("Operations Phase 2 presentes :", len(EXPECTED) - len(missing))

    if missing:
        print("Operations manquantes :")
        for method, path in missing:
            print("-", method, path)
        raise SystemExit(1)

    print("Phase 2 Interventions et Stock : OK")


if __name__ == "__main__":
    main()
