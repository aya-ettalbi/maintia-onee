from __future__ import annotations

from app.main import app


EXPECTED = {
    ("POST", "/api/v1/users/{user_id}/activate"),
    ("POST", "/api/v1/users/{user_id}/deactivate"),
    ("POST", "/api/v1/users/{user_id}/reset-password"),
    ("POST", "/api/v1/equipments/{equipment_id}/activate"),
    ("POST", "/api/v1/maintenance-requests/{request_id}/cancel"),
    ("POST", "/api/v1/notifications/read-all"),
    ("GET", "/api/v1/notifications/unread-count"),
    ("POST", "/api/v1/ai/triage"),
    ("GET", "/api/v1/ai/equipments/{equipment_id}/risk-assessment"),
    ("GET", "/api/v1/ai/analytics/recurrent-failures"),
    ("GET", "/api/v1/ai/stock/shortage-risks"),
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
    print("Routes de complétion attendues :", len(EXPECTED))
    print("Routes présentes :", len(EXPECTED) - len(missing))

    if missing:
        print("Routes manquantes :")
        for method, path in missing:
            print("-", method, path)
        raise SystemExit(1)

    print("Backend completion Phase 1 : OK")


if __name__ == "__main__":
    main()
