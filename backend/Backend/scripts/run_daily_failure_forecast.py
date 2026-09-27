from __future__ import annotations

import argparse
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.enums import Role, UserStatus
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.phase4_failure_forecast import (
    FailureForecastBatchRequest,
)
from app.services.phase4_failure_forecast import (
    run_batch_forecasts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute le batch quotidien de prediction des pannes."
    )
    parser.add_argument("--horizon-days", type=int, default=90)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--all-equipments",
        action="store_true",
        help="Inclut les equipements sans historique lie.",
    )
    parser.add_argument(
        "--no-actions",
        action="store_true",
        help="Ne cree ni notification ni recommandation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with SessionLocal() as db:
        actor = db.scalar(
            select(User)
            .where(
                User.role.in_([Role.ADMIN.value, Role.MANAGER.value]),
                User.status == UserStatus.ACTIVE.value,
            )
            .order_by(User.id.asc())
        )
        if actor is None:
            raise RuntimeError(
                "Aucun ADMIN ou MANAGER actif pour tracer le batch."
            )

        payload = FailureForecastBatchRequest(
            horizon_days=args.horizon_days,
            limit=args.limit,
            offset=args.offset,
            only_with_history=not args.all_equipments,
            create_actions=not args.no_actions,
        )
        result = run_batch_forecasts(
            db,
            payload=payload,
            actor=actor,
        )

    print("Run ID :", result.run_id)
    print("Statut :", result.status)
    print("Traites :", result.processed_count)
    print("HIGH :", result.high_risk_count)
    print("MEDIUM :", result.medium_risk_count)
    print("LOW :", result.low_risk_count)
    print("Notifications :", result.notifications_created)
    print("Recommandations :", result.recommendations_created)
    print("Erreurs :", result.error_count)


if __name__ == "__main__":
    main()
