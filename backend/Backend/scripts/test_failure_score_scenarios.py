from __future__ import annotations

r"""
Test contrôlé du score Phase 4 avec plusieurs nouvelles données.

Ce script crée des équipements QA temporaires, ajoute des historiques,
des interventions correctives et des plans préventifs, puis compare le
score calculé par le Backend avec un score attendu calculé séparément.

Exécution recommandée depuis le dossier Backend :

    python .\scripts\test_failure_score_scenarios.py

Par défaut, toutes les données sont annulées avec ROLLBACK.

Pour conserver les équipements et les prévisions dans PostgreSQL afin de
les afficher dans le Frontend :

    python .\scripts\test_failure_score_scenarios.py --keep-data

Pour supprimer ensuite les données QA conservées :

    python .\scripts\test_failure_score_scenarios.py --cleanup
"""

import argparse
import csv
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = (
    CURRENT_FILE.parents[1]
    if CURRENT_FILE.parent.name.lower() == "scripts"
    else Path.cwd()
)

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.enums import (  # noqa: E402
    EquipmentStatus,
    InterventionStatus,
    MaintenanceType,
    Priority,
    Role,
    UserStatus,
)
from app.db.session import SessionLocal  # noqa: E402
from app.models.ai_core import EquipmentHistoricalLink  # noqa: E402
from app.models.equipment import Equipment, EquipmentCategory  # noqa: E402
from app.models.historical import HistoricalRequest  # noqa: E402
from app.models.maintenance import Intervention  # noqa: E402
from app.models.phase3_preventive import PreventiveMaintenancePlan  # noqa: E402
from app.models.phase4_failure_forecast import FailureForecast  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.phase4_failure_forecast import (  # noqa: E402
    build_forecast_snapshot,
)


QA_PREFIX = "QA_SCORE_"
HORIZON_DAYS = 90


@dataclass(frozen=True)
class Scenario:
    key: str
    description: str
    status: str = EquipmentStatus.IN_SERVICE.value
    age_years: int | None = None
    expired_warranty: bool = False
    corrective_180_days: int = 0
    historical_links: int = 0
    history_age_days: int = 30
    history_family: str = "OPERATING_SYSTEM"
    overdue_preventive_plans: int = 0


SCENARIOS: list[Scenario] = [
    Scenario(
        key="BASELINE",
        description="Équipement neuf sans historique ni intervention.",
    ),
    Scenario(
        key="AGE_WARRANTY",
        description="Équipement de 4 ans avec garantie expirée.",
        age_years=4,
        expired_warranty=True,
    ),
    Scenario(
        key="MAINTENANCE_2_FAILURES",
        description=(
            "Équipement en maintenance avec deux interventions "
            "correctives récentes."
        ),
        status=EquipmentStatus.IN_MAINTENANCE.value,
        corrective_180_days=2,
    ),
    Scenario(
        key="HISTORY_RECURRENCE",
        description=(
            "Trois demandes historiques validées, récentes et de la "
            "même famille de panne."
        ),
        historical_links=3,
        history_age_days=30,
        history_family="OPERATING_SYSTEM",
    ),
    Scenario(
        key="HIGH_LIVE_RISK",
        description=(
            "Équipement en panne, ancien, hors garantie, avec trois "
            "correctifs récents et un plan préventif en retard."
        ),
        status=EquipmentStatus.IN_FAILURE.value,
        age_years=6,
        expired_warranty=True,
        corrective_180_days=3,
        overdue_preventive_plans=1,
    ),
    Scenario(
        key="CAP_100",
        description=(
            "Cas extrême combinant toutes les sources de risque pour "
            "vérifier le plafonnement à 100."
        ),
        status=EquipmentStatus.OUT_OF_SERVICE.value,
        age_years=9,
        expired_warranty=True,
        corrective_180_days=3,
        historical_links=10,
        history_age_days=30,
        history_family="POWER",
        overdue_preventive_plans=2,
    ),
]


@dataclass
class Result:
    scenario: str
    equipment_id: int
    equipment_code: str
    expected_score: float
    actual_score: float
    expected_probability: float
    actual_probability: float
    expected_level: str
    actual_level: str
    expected_corrective_180_days: int
    actual_corrective_180_days: int
    expected_historical_links: int
    actual_historical_links: int
    expected_overdue_plans: int
    actual_overdue_plans: int
    forecast_id: int | None
    passed: bool
    factors: list[str]
    error: str | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def date_years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(
            year=today.year - years,
            month=2,
            day=28,
        )


def calculate_expected_score(scenario: Scenario) -> float:
    """Calcul indépendant reproduisant explicitement la règle métier V1."""
    score = 0.0

    status_points = {
        EquipmentStatus.IN_FAILURE.value: 30,
        EquipmentStatus.OUT_OF_SERVICE.value: 35,
        EquipmentStatus.WAITING_PART.value: 20,
        EquipmentStatus.IN_MAINTENANCE.value: 10,
    }
    score += status_points.get(scenario.status, 0)

    if scenario.age_years is not None:
        if scenario.age_years >= 8:
            score += 25
        elif scenario.age_years >= 5:
            score += 18
        elif scenario.age_years >= 3:
            score += 8

    if scenario.expired_warranty:
        score += 5

    weighted_history = float(scenario.historical_links)
    if weighted_history >= 10:
        score += 25
    elif weighted_history >= 6:
        score += 18
    elif weighted_history >= 3:
        score += 12
    elif weighted_history > 0:
        score += 5

    score += min(scenario.corrective_180_days * 10, 30)

    if scenario.historical_links >= 3:
        score += 12
    elif scenario.historical_links >= 2:
        score += 7

    if scenario.historical_links > 0:
        if scenario.history_age_days <= 365:
            score += 8
        elif scenario.history_age_days <= 730:
            score += 4

    score += min(scenario.overdue_preventive_plans * 12, 24)

    return round(min(score, 100.0), 2)


def expected_probability(score: float) -> float:
    # À 90 jours, le facteur d'horizon vaut 1.
    return round(min(max(score / 100.0, 0.0), 0.95), 4)


def expected_level(
    score_probability: float,
    status_value: str,
) -> str:
    if status_value in {
        EquipmentStatus.IN_FAILURE.value,
        EquipmentStatus.OUT_OF_SERVICE.value,
    }:
        return "HIGH"
    if score_probability >= 0.65:
        return "HIGH"
    if score_probability >= 0.30:
        return "MEDIUM"
    return "LOW"


def family_payload(family: str) -> dict[str, str]:
    values = {
        "OPERATING_SYSTEM": {
            "classification": "Assistance Windows",
            "symptome": "Écran noir et blocage du démarrage Windows",
            "cause": "Système Windows ou démarrage endommagé",
            "solution": "Contrôle du démarrage et réparation Windows",
        },
        "POWER": {
            "classification": "Maintenance UC",
            "symptome": "Ordinateur ne démarre pas correctement",
            "cause": "Problème d'alimentation",
            "solution": "Contrôle et remplacement du bloc d'alimentation",
        },
        "STORAGE": {
            "classification": "Maintenance disque",
            "symptome": "Démarrage lent et erreurs disque",
            "cause": "Disque défaillant",
            "solution": "Diagnostic SMART et remplacement du disque",
        },
    }
    return values.get(
        family,
        {
            "classification": "Maintenance UC",
            "symptome": "Anomalie matérielle",
            "cause": "Cause matérielle à confirmer",
            "solution": "Diagnostic technique complet",
        },
    )


def find_actor_and_technician(db: Session) -> tuple[User, User]:
    actor = db.scalar(
        select(User)
        .where(
            User.role.in_([Role.ADMIN.value, Role.MANAGER.value]),
            User.status == UserStatus.ACTIVE.value,
        )
        .order_by(User.id.asc())
    )
    if actor is None:
        actor = db.scalar(
            select(User)
            .where(User.status == UserStatus.ACTIVE.value)
            .order_by(User.id.asc())
        )
    if actor is None:
        raise RuntimeError("Aucun utilisateur actif disponible.")

    technician = db.scalar(
        select(User)
        .where(
            User.role == Role.TECHNICIAN.value,
            User.status == UserStatus.ACTIVE.value,
        )
        .order_by(User.id.asc())
    )
    if technician is None:
        technician = actor

    return actor, technician


def create_category(
    db: Session,
    run_token: str,
) -> EquipmentCategory:
    category = EquipmentCategory(
        code=f"{QA_PREFIX}CAT_{run_token}",
        name=f"QA Score Test {run_token}",
        description="Catégorie temporaire pour les tests du score Phase 4.",
    )
    db.add(category)
    db.flush()
    return category


def create_equipment(
    db: Session,
    category_id: int,
    scenario: Scenario,
    run_token: str,
) -> Equipment:
    acquisition_date = (
        date_years_ago(scenario.age_years)
        if scenario.age_years is not None
        else None
    )
    warranty_end_date = (
        date.today() - timedelta(days=30)
        if scenario.expired_warranty
        else None
    )

    equipment = Equipment(
        code=f"{QA_PREFIX}{run_token}_{scenario.key}",
        category_id=category_id,
        brand="QA",
        model=scenario.key,
        serial_number=f"{QA_PREFIX}SER_{run_token}_{scenario.key}",
        acquisition_date=acquisition_date,
        commissioning_date=acquisition_date,
        status=scenario.status,
        warranty_end_date=warranty_end_date,
        notes=(
            "Donnée QA créée automatiquement pour vérifier "
            "le calcul du score Phase 4."
        ),
        archived=False,
    )
    db.add(equipment)
    db.flush()
    return equipment


def add_corrective_interventions(
    db: Session,
    equipment_id: int,
    technician_id: int,
    count: int,
    run_token: str,
    scenario_key: str,
) -> None:
    now = utc_now()

    for index in range(count):
        created_at = now - timedelta(days=20 + index)
        intervention = Intervention(
            reference=(
                f"{QA_PREFIX}INT_{run_token}_{scenario_key}_{index + 1}"
            ),
            request_id=None,
            equipment_id=equipment_id,
            technician_id=technician_id,
            maintenance_type=MaintenanceType.CORRECTIVE.value,
            diagnosis="TEST QA - panne corrective récente",
            solution="TEST QA - contrôle et remise en service",
            status=InterventionStatus.COMPLETED.value,
            started_at=created_at,
            ended_at=created_at + timedelta(hours=2),
            estimated_cost=Decimal("100.00"),
            actual_cost=Decimal("100.00"),
            test_result="TEST QA - résultat validé",
            closed_by_id=technician_id,
            created_at=created_at,
            updated_at=created_at + timedelta(hours=2),
        )
        db.add(intervention)

    db.flush()


def add_historical_links(
    db: Session,
    equipment_id: int,
    scenario: Scenario,
    run_token: str,
) -> None:
    payload = family_payload(scenario.history_family)
    request_date = utc_now() - timedelta(days=scenario.history_age_days)

    for index in range(scenario.historical_links):
        reference = (
            f"{QA_PREFIX}HIST_{run_token}_{scenario.key}_{index + 1}"
        )
        request = HistoricalRequest(
            source_key=reference,
            numero_demande=reference,
            date_creation_demande=request_date - timedelta(days=index),
            date_resolution_demande=(
                request_date - timedelta(days=index) + timedelta(hours=4)
            ),
            nature_demande=payload["classification"],
            description_demande=payload["symptome"],
            classification=payload["classification"],
            detail_classification=scenario.history_family,
            statut="RESOLU",
            symptome=payload["symptome"],
            cause=payload["cause"],
            solution=payload["solution"],
            source_file="qa_failure_score_test.py",
            raw_data={
                "qa": True,
                "run_token": run_token,
                "scenario": scenario.key,
            },
        )
        db.add(request)
        db.flush()

        link = EquipmentHistoricalLink(
            equipment_id=equipment_id,
            historical_request_id=request.id,
            link_method="CODE_EQUIPEMENT_EXACT",
            confidence_score=1.0,
            validation_status="VALIDE",
            source_reference=reference,
            notes="Lien QA exact et validé pour test du score.",
        )
        db.add(link)

    db.flush()


def add_overdue_plans(
    db: Session,
    equipment_id: int,
    actor_id: int,
    technician_id: int,
    count: int,
    run_token: str,
    scenario_key: str,
) -> None:
    for index in range(count):
        plan = PreventiveMaintenancePlan(
            equipment_id=equipment_id,
            title=(
                f"{QA_PREFIX}PLAN_{run_token}_{scenario_key}_{index + 1}"
            ),
            description="Plan QA volontairement en retard.",
            frequency_days=30,
            priority=Priority.HIGH.value,
            assigned_technician_id=technician_id,
            active=True,
            next_due_date=date.today() - timedelta(days=index + 1),
            last_executed_at=None,
            created_by_id=actor_id,
        )
        db.add(plan)

    db.flush()


def save_forecast(
    db: Session,
    snapshot: dict[str, Any],
    actor_id: int,
) -> FailureForecast:
    forecast = FailureForecast(
        equipment_id=snapshot["equipment"].id,
        horizon_days=snapshot["horizon_days"],
        risk_score=snapshot["risk_score"],
        failure_probability=snapshot["failure_probability"],
        probability_calibrated=False,
        risk_level=snapshot["risk_level"],
        evidence_confidence=snapshot["evidence_confidence"],
        predicted_failure_family=snapshot[
            "predicted_failure_family"
        ],
        estimated_start_date=snapshot["estimated_start_date"],
        estimated_end_date=snapshot["estimated_end_date"],
        factors=snapshot["factors"],
        recommended_actions=snapshot["recommended_actions"],
        evidence_summary=snapshot["evidence_summary"],
        similar_references=snapshot["similar_references"],
        explanation=snapshot["explanation"],
        methodology_version=snapshot["methodology_version"],
        llm_used=False,
        model_name="qa-deterministic-forecast",
        recommendation_id=None,
        notification_created=False,
        validation_status="PENDING",
        created_by_id=actor_id,
    )
    db.add(forecast)
    db.flush()
    return forecast


def evaluate_scenario(
    db: Session,
    scenario: Scenario,
    category_id: int,
    actor: User,
    technician: User,
    run_token: str,
    keep_data: bool,
) -> Result:
    equipment = create_equipment(
        db,
        category_id=category_id,
        scenario=scenario,
        run_token=run_token,
    )

    add_corrective_interventions(
        db,
        equipment_id=equipment.id,
        technician_id=technician.id,
        count=scenario.corrective_180_days,
        run_token=run_token,
        scenario_key=scenario.key,
    )
    add_historical_links(
        db,
        equipment_id=equipment.id,
        scenario=scenario,
        run_token=run_token,
    )
    add_overdue_plans(
        db,
        equipment_id=equipment.id,
        actor_id=actor.id,
        technician_id=technician.id,
        count=scenario.overdue_preventive_plans,
        run_token=run_token,
        scenario_key=scenario.key,
    )

    snapshot = build_forecast_snapshot(
        db,
        equipment_id=equipment.id,
        horizon_days=HORIZON_DAYS,
    )

    expected_score_value = calculate_expected_score(scenario)
    expected_probability_value = expected_probability(
        expected_score_value
    )
    expected_level_value = expected_level(
        expected_probability_value,
        scenario.status,
    )

    evidence = snapshot["evidence_summary"]
    actual_corrective = int(
        evidence["live_interventions"]["corrective_180_days"]
    )
    actual_history = int(
        evidence["historical"]["linked_requests"]
    )
    actual_overdue = int(
        evidence["overdue_preventive_plans"]
    )

    checks = [
        abs(snapshot["risk_score"] - expected_score_value) < 0.001,
        abs(
            snapshot["failure_probability"]
            - expected_probability_value
        )
        < 0.001,
        snapshot["risk_level"] == expected_level_value,
        actual_corrective == scenario.corrective_180_days,
        actual_history == scenario.historical_links,
        actual_overdue == scenario.overdue_preventive_plans,
        snapshot["probability_calibrated"] is False,
        snapshot["methodology_version"] == "HEURISTIC_HISTORY_V1",
    ]

    forecast_id = None
    if keep_data:
        forecast = save_forecast(
            db,
            snapshot=snapshot,
            actor_id=actor.id,
        )
        forecast_id = forecast.id

    return Result(
        scenario=scenario.key,
        equipment_id=equipment.id,
        equipment_code=equipment.code,
        expected_score=expected_score_value,
        actual_score=float(snapshot["risk_score"]),
        expected_probability=expected_probability_value,
        actual_probability=float(snapshot["failure_probability"]),
        expected_level=expected_level_value,
        actual_level=str(snapshot["risk_level"]),
        expected_corrective_180_days=scenario.corrective_180_days,
        actual_corrective_180_days=actual_corrective,
        expected_historical_links=scenario.historical_links,
        actual_historical_links=actual_history,
        expected_overdue_plans=scenario.overdue_preventive_plans,
        actual_overdue_plans=actual_overdue,
        forecast_id=forecast_id,
        passed=all(checks),
        factors=list(snapshot["factors"]),
    )


def cleanup_qa_data(db: Session) -> int:
    equipment_ids = list(
        db.scalars(
            select(Equipment.id).where(
                Equipment.code.like(f"{QA_PREFIX}%")
            )
        ).all()
    )

    historical_ids = list(
        db.scalars(
            select(HistoricalRequest.id).where(
                HistoricalRequest.source_key.like(f"{QA_PREFIX}%")
            )
        ).all()
    )

    if equipment_ids:
        db.execute(
            delete(FailureForecast).where(
                FailureForecast.equipment_id.in_(equipment_ids)
            )
        )
        db.execute(
            delete(PreventiveMaintenancePlan).where(
                PreventiveMaintenancePlan.equipment_id.in_(
                    equipment_ids
                )
            )
        )
        db.execute(
            delete(EquipmentHistoricalLink).where(
                EquipmentHistoricalLink.equipment_id.in_(
                    equipment_ids
                )
            )
        )
        db.execute(
            delete(Intervention).where(
                Intervention.equipment_id.in_(equipment_ids)
            )
        )
        db.execute(
            delete(Equipment).where(
                Equipment.id.in_(equipment_ids)
            )
        )

    if historical_ids:
        db.execute(
            delete(EquipmentHistoricalLink).where(
                EquipmentHistoricalLink.historical_request_id.in_(
                    historical_ids
                )
            )
        )
        db.execute(
            delete(HistoricalRequest).where(
                HistoricalRequest.id.in_(historical_ids)
            )
        )

    db.execute(
        delete(EquipmentCategory).where(
            EquipmentCategory.code.like(f"{QA_PREFIX}%")
        )
    )

    db.commit()
    return len(equipment_ids)


def save_report(
    results: list[Result],
    run_token: str,
    keep_data: bool,
) -> tuple[Path, Path]:
    report_dir = BACKEND_ROOT / "qa_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = (
        report_dir
        / f"failure_score_test_{run_token}.json"
    )
    csv_path = (
        report_dir
        / f"failure_score_test_{run_token}.csv"
    )

    payload = {
        "generated_at": utc_now().isoformat(),
        "horizon_days": HORIZON_DAYS,
        "kept_in_database": keep_data,
        "total": len(results),
        "passed": sum(1 for item in results if item.passed),
        "failed": sum(1 for item in results if not item.passed),
        "results": [asdict(item) for item in results],
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "scenario",
        "equipment_id",
        "equipment_code",
        "expected_score",
        "actual_score",
        "expected_probability",
        "actual_probability",
        "expected_level",
        "actual_level",
        "expected_corrective_180_days",
        "actual_corrective_180_days",
        "expected_historical_links",
        "actual_historical_links",
        "expected_overdue_plans",
        "actual_overdue_plans",
        "forecast_id",
        "passed",
        "error",
    ]

    with csv_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        for result in results:
            row = asdict(result)
            row.pop("factors", None)
            writer.writerow(row)

    return json_path, csv_path


def print_result(result: Result) -> None:
    marker = "OK" if result.passed else "ECHEC"
    print(
        f"[{marker}] {result.scenario:<24} "
        f"score {result.actual_score:>6.2f} "
        f"(attendu {result.expected_score:>6.2f}) | "
        f"{result.actual_level:<6} | "
        f"correctifs {result.actual_corrective_180_days} | "
        f"historique {result.actual_historical_links} | "
        f"retards {result.actual_overdue_plans}"
    )
    if result.error:
        print(f"        Erreur : {result.error}")
    for factor in result.factors:
        print(f"        - {factor}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Teste le calcul Phase 4 avec plusieurs nouvelles "
            "données contrôlées."
        )
    )
    parser.add_argument(
        "--keep-data",
        action="store_true",
        help=(
            "Conserve les équipements, historiques, interventions, "
            "plans et prévisions QA dans PostgreSQL."
        ),
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Supprime toutes les données dont le code commence par QA_SCORE_.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with SessionLocal() as db:
        if args.cleanup:
            removed = cleanup_qa_data(db)
            print(
                f"Nettoyage terminé : {removed} équipement(s) QA supprimé(s)."
            )
            return

        actor, technician = find_actor_and_technician(db)
        run_token = uuid.uuid4().hex[:8].upper()
        results: list[Result] = []

        print("=" * 100)
        print("TEST CONTRÔLÉ DU SCORE DE RISQUE PHASE 4")
        print("=" * 100)
        print(f"Run             : {run_token}")
        print(f"Horizon         : {HORIZON_DAYS} jours")
        print(f"Acteur          : {actor.email} (id={actor.id})")
        print(
            f"Technicien      : {technician.email} "
            f"(id={technician.id})"
        )
        print(
            "Persistance      : "
            + (
                "OUI, données conservées"
                if args.keep_data
                else "NON, rollback automatique"
            )
        )
        print()

        try:
            category = create_category(db, run_token)

            for scenario in SCENARIOS:
                try:
                    with db.begin_nested():
                        result = evaluate_scenario(
                            db,
                            scenario=scenario,
                            category_id=category.id,
                            actor=actor,
                            technician=technician,
                            run_token=run_token,
                            keep_data=args.keep_data,
                        )
                    results.append(result)
                    print_result(result)
                except Exception as error:
                    result = Result(
                        scenario=scenario.key,
                        equipment_id=0,
                        equipment_code="",
                        expected_score=calculate_expected_score(
                            scenario
                        ),
                        actual_score=-1,
                        expected_probability=expected_probability(
                            calculate_expected_score(scenario)
                        ),
                        actual_probability=-1,
                        expected_level=expected_level(
                            expected_probability(
                                calculate_expected_score(scenario)
                            ),
                            scenario.status,
                        ),
                        actual_level="ERROR",
                        expected_corrective_180_days=(
                            scenario.corrective_180_days
                        ),
                        actual_corrective_180_days=-1,
                        expected_historical_links=(
                            scenario.historical_links
                        ),
                        actual_historical_links=-1,
                        expected_overdue_plans=(
                            scenario.overdue_preventive_plans
                        ),
                        actual_overdue_plans=-1,
                        forecast_id=None,
                        passed=False,
                        factors=[],
                        error=str(error),
                    )
                    results.append(result)
                    print_result(result)

            json_path, csv_path = save_report(
                results,
                run_token=run_token,
                keep_data=args.keep_data,
            )

            failures = [
                result
                for result in results
                if not result.passed
            ]

            if args.keep_data:
                db.commit()
            else:
                db.rollback()

            print()
            print("=" * 100)
            print(
                f"Résultat : {len(results) - len(failures)}/{len(results)} "
                "scénarios conformes"
            )
            print(f"Rapport JSON : {json_path}")
            print(f"Rapport CSV  : {csv_path}")

            if args.keep_data:
                print()
                print(
                    "Les données QA sont conservées. Dans le Frontend, "
                    f"recherchez le préfixe {QA_PREFIX}."
                )
                print(
                    "Pour les supprimer : "
                    "python .\\scripts\\test_failure_score_scenarios.py "
                    "--cleanup"
                )
            else:
                print(
                    "Toutes les données QA ont été annulées avec ROLLBACK."
                )

            if failures:
                raise SystemExit(1)

            print("CALCUL DU SCORE PHASE 4 : VALIDÉ")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
