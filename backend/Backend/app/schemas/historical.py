from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HistoricalSummary(BaseModel):
    requests_count: int
    tasks_count: int
    it_supplies_count: int
    office_supplies_count: int
    security_incidents_count: int
    total_historical_rows: int
    operational_requests_count: int
    combined_requests_count: int
    operational_interventions_count: int
    combined_interventions_count: int


class HistoricalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_demande: str
    date_creation_demande: datetime | None
    date_resolution_demande: datetime | None
    nature_demande: str | None
    description_demande: str | None
    classification: str | None
    detail_classification: str | None
    statut: str | None
    demandeur: str | None
    matricule: str | None
    nom_demandeur: str | None
    prenom_demandeur: str | None
    adresse_mail: str | None
    sigle: str | None
    beneficiaire: str | None
    groupe_intervenants: str | None
    dernier_intervenant: str | None
    symptome: str | None
    cause: str | None
    solution: str | None


class HistoricalTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_tache: str
    numero_demande: str | None
    date_creation_tache: datetime | None
    date_fin_tache: datetime | None
    description_tache: str | None
    statut_tache: str | None
    intervenant: str | None
    groupe_intervenant: str | None
    classification_tache: str | None
    motif_rejet: str | None
    detail_demande: str | None
    classification_demande: str | None
    demandeur: str | None
    adresse_mail: str | None


class HistoricalITSupplyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_demande: str | None
    date_initiation: datetime | None
    date_traitement: datetime | None
    etape_en_cours: str | None
    initiateur: str | None
    login_initiateur: str | None
    direction: str | None
    motif_demande: str | None
    nom_recepteur: str | None
    matricule_recepteur: str | None
    articles: str | None


class HistoricalOfficeSupplyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str | None
    reference_consolidee: str | None
    date_initiation: datetime | None
    date_traitement: datetime | None
    expediteur: str | None
    etape_en_cours: str | None
    direction: str | None
    code_source: str | None


class HistoricalSecurityIncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_fiche: str | None
    statut: str | None
    etape_en_cours: str | None
    date_initiation: datetime | None
    date_traitement: datetime | None
    date_cloture: datetime | None
    nom_initiateur: str | None
    sigle_initiateur: str | None
    description_incident: str | None
    cause_incident: str | None
    impact_incident: str | None
    action_curative: str | None
    action_corrective: str | None
    criticite: str | None
    groupe_traitement: str | None


class RequestPage(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[HistoricalRequestRead]


class TaskPage(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[HistoricalTaskRead]


class ITSupplyPage(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[HistoricalITSupplyRead]


class OfficeSupplyPage(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[HistoricalOfficeSupplyRead]


class SecurityIncidentPage(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[HistoricalSecurityIncidentRead]


class HistoricalCountItem(BaseModel):
    name: str
    value: int


class HistoricalMonthlyItem(BaseModel):
    month: str
    value: int


class HistoricalAnalytics(BaseModel):
    request_statuses: list[HistoricalCountItem]
    request_classifications: list[HistoricalCountItem]
    task_statuses: list[HistoricalCountItem]
    top_technicians: list[HistoricalCountItem]
    monthly_requests: list[HistoricalMonthlyItem]
    requests_with_cause: int
    requests_with_solution: int
    average_resolution_hours: float | None


class HistoricalDiagnosticRequest(BaseModel):
    description: str = Field(min_length=5, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=10)


class HistoricalDiagnosticSuggestion(BaseModel):
    intervention_id: int
    similarity: float
    diagnosis: str | None
    solution: str | None
