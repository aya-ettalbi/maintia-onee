from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.historical import (
    HistoricalITSupply,
    HistoricalOfficeSupply,
    HistoricalRequest,
    HistoricalSecurityIncident,
    HistoricalTask,
)


DEFAULT_DATA_DIR = Path(
    r"C:\Users\hp\OneDrive\Desktop\Projet_Maintenance_Intelligente_ONEE"
    r"\05_Donnees\Donnees_Nettoyees\CSV"
)


FILE_PATTERNS = {
    "requests": ["khadamate.csv", "khadamate(1).csv"],
    "tasks": ["khadamate_taches.csv", "khadamate_taches(1).csv"],
    "it": ["fournitures_informatiques.csv", "fournitures_informatiques(1).csv"],
    "office": ["fournitures_bureaux.csv", "fournitures_bureaux(1).csv"],
    "security": ["himaya.csv", "himaya(1).csv"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import complet des données historiques ONEE.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--batch-size", type=int, default=1000)
    return parser.parse_args()


def find_file(data_dir: Path, names: list[str]) -> Path:
    for name in names:
        direct = data_dir / name
        if direct.exists():
            return direct

    lowered = {name.lower() for name in names}
    for path in data_dir.rglob("*.csv"):
        if path.name.lower() in lowered:
            return path

    raise FileNotFoundError(
        f"Fichier introuvable dans {data_dir}. Noms cherchés : {', '.join(names)}"
    )


def missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False



def first_non_missing(*values: Any) -> Any:
    for value in values:
        if not missing(value):
            return value
    return None


def txt(value: Any, max_length: int | None = None) -> str | None:
    if missing(value):
        return None

    value = str(value).strip()
    if not value:
        return None

    if value.endswith(".0") and value[:-2].isdigit():
        value = value[:-2]

    return value[:max_length] if max_length else value


def dt(value: Any) -> datetime | None:
    if missing(value):
        return None

    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None

    result = parsed.to_pydatetime()
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result


def safe_json(value: Any) -> Any:
    if missing(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, (str, int, bool)):
        return value
    return str(value)


def raw_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(k): safe_json(v) for k, v in row.items()}


def source_key(dataset: str, natural_key: str | None, row_number: int, row: dict[str, Any]) -> str:
    if natural_key:
        return f"{dataset}:{natural_key}"

    payload = json.dumps(raw_row(row), ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{dataset}:ROW-{row_number}:{digest}"


def request_mapping(row: dict[str, Any], row_number: int, source_file: str) -> dict[str, Any]:
    numero = txt(row.get("numero_demande"), 100)
    return {
        "source_key": source_key("REQ", numero, row_number, row),
        "numero_demande": numero or f"SANS-NUMERO-{row_number}",
        "date_creation_demande": dt(row.get("date_creation_demande")),
        "date_resolution_demande": dt(row.get("date_resolution_demande")),
        "nature_demande": txt(row.get("nature_demande"), 255),
        "description_demande": txt(row.get("description_demande")),
        "classification": txt(row.get("classification"), 255),
        "detail_classification": txt(row.get("detail_classification"), 255),
        "statut": txt(row.get("statut"), 100),
        "demandeur": txt(row.get("demandeur"), 255),
        "matricule": txt(row.get("matricule"), 100),
        "nom_demandeur": txt(row.get("nom_demandeur"), 150),
        "prenom_demandeur": txt(row.get("prenom_demandeur"), 150),
        "adresse_mail": txt(row.get("adresse_mail"), 255),
        "sigle": txt(row.get("sigle"), 100),
        "beneficiaire": txt(row.get("beneficiaire"), 255),
        "groupe_intervenants": txt(row.get("groupe_d_intervenants"), 255),
        "dernier_intervenant": txt(row.get("dernier_intervenant"), 255),
        "symptome": txt(row.get("symptome")),
        "cause": txt(row.get("cause")),
        "solution": txt(row.get("solution")),
        "source_file": source_file,
        "raw_data": raw_row(row),
    }


def task_mapping(row: dict[str, Any], row_number: int, source_file: str) -> dict[str, Any]:
    numero_tache = txt(row.get("numero_tache"), 100)
    return {
        "source_key": source_key("TASK", numero_tache, row_number, row),
        "numero_tache": numero_tache or f"SANS-NUMERO-{row_number}",
        "numero_demande": txt(row.get("numero_demande"), 100),
        "date_creation_tache": dt(row.get("date_creation_tache")),
        "date_fin_tache": dt(row.get("date_fin_tache")),
        "description_tache": txt(row.get("description_tache")),
        "statut_tache": txt(row.get("statut_1"), 100),
        "intervenant": txt(row.get("intervenant"), 255),
        "groupe_intervenant": txt(row.get("groupe_intervenant"), 255),
        "classification_tache": txt(row.get("classification_tache"), 255),
        "motif_rejet": txt(row.get("motif_rejet_1")),
        "detail_demande": txt(row.get("detail_demande")),
        "classification_demande": txt(row.get("classification"), 255),
        "demandeur": txt(row.get("demandeur"), 255),
        "adresse_mail": txt(row.get("adresse_mail"), 255),
        "source_file": source_file,
        "raw_data": raw_row(row),
    }


def it_mapping(row: dict[str, Any], row_number: int, source_file: str) -> dict[str, Any]:
    numero = txt(row.get("numero_demande"), 100)
    return {
        "source_key": source_key("IT", numero, row_number, row),
        "numero_demande": numero,
        "date_initiation": dt(first_non_missing(row.get("date_initiation"), row.get("date_d_initiation"))),
        "date_traitement": dt(row.get("date_de_traitement")),
        "etape_en_cours": txt(row.get("etape_en_cours"), 255),
        "initiateur": txt(row.get("initiateur"), 255),
        "login_initiateur": txt(row.get("logininitiateur"), 255),
        "direction": txt(row.get("direction"), 100),
        "motif_demande": txt(row.get("motif_de_la_demande")),
        "nom_recepteur": txt(row.get("nom_recepteur"), 255),
        "matricule_recepteur": txt(row.get("matricule_recepteur"), 100),
        "articles": txt(row.get("articles")),
        "source_file": source_file,
        "raw_data": raw_row(row),
    }


def office_mapping(row: dict[str, Any], row_number: int, source_file: str) -> dict[str, Any]:
    reference = txt(row.get("reference"), 150)
    natural = reference or txt(row.get("reference_de_la_demande_consolidee_exceptionnelle"), 150)
    return {
        "source_key": source_key("OFFICE", natural, row_number, row),
        "reference": reference,
        "reference_consolidee": txt(
            row.get("reference_de_la_demande_consolidee_exceptionnelle"), 150
        ),
        "date_initiation": dt(row.get("date_d_initiation")),
        "date_traitement": dt(row.get("date_de_traitement")),
        "expediteur": txt(row.get("expediteur"), 255),
        "etape_en_cours": txt(row.get("etape_en_cours"), 255),
        "direction": txt(row.get("direction"), 100),
        "code_source": txt(row.get("unnamed_6"), 100),
        "source_file": source_file,
        "raw_data": raw_row(row),
    }


def security_mapping(row: dict[str, Any], row_number: int, source_file: str) -> dict[str, Any]:
    numero = txt(row.get("numero_fiche"), 150)
    return {
        "source_key": source_key("SEC", numero, row_number, row),
        "numero_fiche": numero,
        "statut": txt(row.get("statut"), 100),
        "etape_en_cours": txt(row.get("etape_en_cours"), 255),
        "date_initiation": dt(first_non_missing(row.get("date_initiation"), row.get("date_d_initiation"))),
        "date_traitement": dt(row.get("date_de_traitement")),
        "date_cloture": dt(row.get("date_cloture")),
        "nom_initiateur": txt(row.get("nom_initiateur"), 255),
        "sigle_initiateur": txt(row.get("sigle_initateur"), 100),
        "description_incident": txt(row.get("description_de_l_incident")),
        "cause_incident": txt(row.get("causes_de_l_incident_releve")),
        "impact_incident": txt(row.get("impact_de_l_incident")),
        "action_curative": txt(first_non_missing(row.get("action_curative_proposee"), row.get("action_curative"))),
        "action_corrective": txt(row.get("action_corrective")),
        "criticite": txt(row.get("niveau_de_criticite"), 100),
        "groupe_traitement": txt(row.get("groupe_de_traitement"), 255),
        "source_file": source_file,
        "raw_data": raw_row(row),
    }


DATASETS = [
    ("Demandes Khadamate", HistoricalRequest, FILE_PATTERNS["requests"], request_mapping),
    ("Tâches Khadamate", HistoricalTask, FILE_PATTERNS["tasks"], task_mapping),
    ("Fournitures informatiques", HistoricalITSupply, FILE_PATTERNS["it"], it_mapping),
    ("Fournitures bureaux", HistoricalOfficeSupply, FILE_PATTERNS["office"], office_mapping),
    ("Incidents Himaya", HistoricalSecurityIncident, FILE_PATTERNS["security"], security_mapping),
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        sep=";",
        encoding="utf-8-sig",
        dtype=object,
        keep_default_na=True,
    )


def prepare(
    df: pd.DataFrame,
    mapper: Callable[[dict[str, Any], int, str], dict[str, Any]],
    source_file: str,
) -> tuple[list[dict[str, Any]], int]:
    rows = []
    duplicates = 0
    seen = set()

    for row_number, row in enumerate(df.to_dict(orient="records"), start=1):
        mapped = mapper(row, row_number, source_file)
        key = mapped["source_key"]

        if key in seen:
            duplicates += 1
            continue

        seen.add(key)
        rows.append(mapped)

    return rows, duplicates


def insert_dataset(db, model, rows: list[dict[str, Any]], batch_size: int, commit: bool):
    existing = set(db.scalars(select(model.source_key)).all())
    new_rows = [row for row in rows if row["source_key"] not in existing]
    already_existing = len(rows) - len(new_rows)

    if commit:
        for start in range(0, len(new_rows), batch_size):
            batch = new_rows[start:start + batch_size]
            db.bulk_insert_mappings(model, batch)
            db.flush()
            print(f"      lot {start + len(batch)}/{len(new_rows)}")

    return len(new_rows), already_existing


def main() -> None:
    args = parse_args()

    print("=" * 80)
    print("IMPORT COMPLET DES DONNEES HISTORIQUES ONEE")
    print("=" * 80)
    print("Mode :", "ECRITURE REELLE" if args.commit else "SIMULATION SANS ECRITURE")
    print("Dossier :", args.data_dir)

    report = {
        "mode": "commit" if args.commit else "dry-run",
        "data_dir": str(args.data_dir),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "datasets": {},
    }

    with SessionLocal() as db:
        try:
            for label, model, names, mapper in DATASETS:
                path = find_file(args.data_dir, names)
                df = read_csv(path)
                rows, duplicates = prepare(df, mapper, path.name)

                print(f"\n{label}")
                print(f"  Fichier                : {path}")
                print(f"  Lignes CSV             : {len(df)}")
                print(f"  Lignes préparées       : {len(rows)}")
                print(f"  Doublons internes      : {duplicates}")

                new_count, existing_count = insert_dataset(
                    db, model, rows, args.batch_size, args.commit
                )

                print(f"  Nouvelles lignes       : {new_count}")
                print(f"  Déjà présentes         : {existing_count}")

                report["datasets"][model.__tablename__] = {
                    "file": str(path),
                    "csv_rows": len(df),
                    "prepared_rows": len(rows),
                    "internal_duplicates": duplicates,
                    "new_rows": new_count,
                    "already_existing": existing_count,
                }

            if args.commit:
                db.commit()
                print("\n[OK] Import validé dans PostgreSQL.")
            else:
                db.rollback()
                print("\n[OK] Simulation terminée. Aucune donnée écrite.")

        except Exception:
            db.rollback()
            print("\n[ERREUR] Transaction annulée.")
            raise

    report["finished_at"] = datetime.now(timezone.utc).isoformat()

    reports_dir = args.data_dir.parent / "Rapports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"rapport_import_historique_{timestamp}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Rapport :", report_path)
    print("=" * 80)


if __name__ == "__main__":
    main()
