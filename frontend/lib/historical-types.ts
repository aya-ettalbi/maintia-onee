export type HistoricalSummary = {
  requests_count: number
  tasks_count: number
  it_supplies_count: number
  office_supplies_count: number
  security_incidents_count: number
  total_historical_rows: number
  operational_requests_count: number
  combined_requests_count: number
  operational_interventions_count: number
  combined_interventions_count: number
}

export type HistoricalRequest = {
  id: number
  numero_demande: string
  date_creation_demande: string | null
  date_resolution_demande: string | null
  nature_demande: string | null
  description_demande: string | null
  classification: string | null
  detail_classification: string | null
  statut: string | null
  demandeur: string | null
  matricule: string | null
  nom_demandeur: string | null
  prenom_demandeur: string | null
  adresse_mail: string | null
  sigle: string | null
  beneficiaire: string | null
  groupe_intervenants: string | null
  dernier_intervenant: string | null
  symptome: string | null
  cause: string | null
  solution: string | null
}

export type HistoricalTask = {
  id: number
  numero_tache: string
  numero_demande: string | null
  date_creation_tache: string | null
  date_fin_tache: string | null
  description_tache: string | null
  statut_tache: string | null
  intervenant: string | null
  groupe_intervenant: string | null
  classification_tache: string | null
  motif_rejet: string | null
  detail_demande: string | null
  classification_demande: string | null
  demandeur: string | null
  adresse_mail: string | null
}

export type HistoricalITSupply = {
  id: number
  numero_demande: string | null
  date_initiation: string | null
  date_traitement: string | null
  etape_en_cours: string | null
  initiateur: string | null
  login_initiateur: string | null
  direction: string | null
  motif_demande: string | null
  nom_recepteur: string | null
  matricule_recepteur: string | null
  articles: string | null
}

export type HistoricalOfficeSupply = {
  id: number
  reference: string | null
  reference_consolidee: string | null
  date_initiation: string | null
  date_traitement: string | null
  expediteur: string | null
  etape_en_cours: string | null
  direction: string | null
  code_source: string | null
}

export type HistoricalSecurityIncident = {
  id: number
  numero_fiche: string | null
  statut: string | null
  etape_en_cours: string | null
  date_initiation: string | null
  date_traitement: string | null
  date_cloture: string | null
  nom_initiateur: string | null
  sigle_initiateur: string | null
  description_incident: string | null
  cause_incident: string | null
  impact_incident: string | null
  action_curative: string | null
  action_corrective: string | null
  criticite: string | null
  groupe_traitement: string | null
}

export type HistoricalPage<T> = {
  total: number
  skip: number
  limit: number
  items: T[]
}

export type HistoricalCountItem = {
  name: string
  value: number
}

export type HistoricalMonthlyItem = {
  month: string
  value: number
}

export type HistoricalAnalytics = {
  request_statuses: HistoricalCountItem[]
  request_classifications: HistoricalCountItem[]
  task_statuses: HistoricalCountItem[]
  top_technicians: HistoricalCountItem[]
  monthly_requests: HistoricalMonthlyItem[]
  requests_with_cause: number
  requests_with_solution: number
  average_resolution_hours: number | null
}
