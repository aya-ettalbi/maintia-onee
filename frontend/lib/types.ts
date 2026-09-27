export type Role = "ADMIN" | "MANAGER" | "TECHNICIAN" | "STOCK_MANAGER" | "REQUESTER"

export type User = {
  id: number
  first_name: string
  last_name: string
  email: string
  role: Role | string
  status: string
  service_id: number | null
  created_at: string
  updated_at: string
}

export type DashboardSummary = {
  total_equipments: number
  equipments_in_service: number
  equipments_in_failure: number
  open_requests: number
  active_interventions: number
  low_stock_parts: number
  open_recommendations: number
  average_repair_hours: number | null
}

export type OrganizationItem = {
  id: number
  code: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export type EquipmentCategory = OrganizationItem

export type Equipment = {
  id: number
  code: string
  category_id: number
  brand: string | null
  model: string | null
  serial_number: string | null
  acquisition_date: string | null
  commissioning_date: string | null
  status: string
  location_id: number | null
  current_service_id: number | null
  warranty_end_date: string | null
  notes: string | null
  archived: boolean
  created_at: string
  updated_at: string
}

export type EquipmentAssignment = {
  id: number
  equipment_id: number
  user_id: number | null
  service_id: number | null
  assigned_at: string
  returned_at: string | null
  is_active: boolean
  comment: string | null
  created_at: string
  updated_at: string
}

export type MaintenanceRequest = {
  id: number
  reference: string
  equipment_id: number
  requester_id: number
  assigned_technician_id: number | null
  description: string
  category: string | null
  priority: string
  status: string
  submitted_at: string
  assigned_at: string | null
  closed_at: string | null
  created_at: string
  updated_at: string
}

export type Intervention = {
  id: number
  reference: string
  request_id: number | null
  equipment_id: number
  technician_id: number
  maintenance_type: string
  diagnosis: string | null
  solution: string | null
  status: string
  started_at: string | null
  ended_at: string | null
  estimated_cost: string | number
  actual_cost: string | number
  test_result: string | null
  closed_by_id: number | null
  created_at: string
  updated_at: string
}

export type InterventionStatusHistory = {
  id: number
  intervention_id: number
  old_status: string | null
  new_status: string
  changed_by_id: number
  comment: string | null
  changed_at: string
  created_at: string
  updated_at: string
}

export type InterventionAction = {
  id: number
  intervention_id: number
  description: string
  performed_by_id: number
  performed_at: string
  created_at: string
  updated_at: string
}

export type InterventionPart = {
  id: number
  intervention_id: number
  part_id: number
  quantity: number
  unit_price: string | number
  created_at: string
  updated_at?: string
}

export type SparePart = {
  id: number
  code: string
  name: string
  category: string | null
  quantity: number
  minimum_threshold: number
  unit_price: string | number
  supplier: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export type StockMovement = {
  id: number
  part_id: number
  movement_type: string
  quantity: number
  unit_cost: string | number
  intervention_id: number | null
  performed_by_id: number
  reason: string | null
  created_at: string
}

export type StockSummary = {
  total_parts: number
  active_parts: number
  total_quantity: number
  low_stock_parts: number
  out_of_stock_parts: number
  inventory_value: string
}

export type StockAlert = {
  part_id: number
  code: string
  name: string
  quantity: number
  minimum_threshold: number
  shortage: number
  suggested_order_quantity: number
  risk: string
}

export type StockAlertsResponse = { total: number; items: StockAlert[] }

export type Recommendation = {
  id: number
  equipment_id: number | null
  part_id: number | null
  recommendation_type: string
  priority: string
  title: string
  observation: string
  justification: string
  recommended_action: string
  risk_score: number
  risk_level: string
  status: string
  due_date: string | null
  generated_at: string
  validated_by_id: number | null
  created_at: string
  updated_at: string
}

export type Notification = {
  id: number
  user_id: number
  title: string
  message: string
  read_at: string | null
  created_at: string
}

export type DiagnosticSuggestion = {
  intervention_id: number
  similarity: number
  diagnosis: string | null
  solution: string | null
}

export type RiskScore = {
  equipment_id: number
  score: number
  level: string
  factors: string[]
  recommended_action: string
}

export type RiskAssessment = {
  equipment_id: number
  equipment_code: string
  score: number
  level: string
  factors: string[]
  recommended_action: string
  calculation_version: string
  metrics: Record<string, number | string | null>
  calculated_at: string
}

export type TriageResponse = {
  incident_type: string
  classification_group: string
  suggested_priority: string
  suggested_team: string
  confidence: string
  confidence_score: number
  matched_rules: string[]
  equipment_code: string | null
  human_validation_required: boolean
}

export type RecurrentFailure = {
  classification: string
  occurrence_count: number
  latest_date: string | null
}

export type RecurrentFailuresResponse = {
  period_months: number
  minimum_occurrences: number
  total_groups: number
  items: RecurrentFailure[]
}

export type StockShortageRisk = {
  part_id: number
  part_code: string
  part_name: string
  current_quantity: number
  minimum_threshold: number
  outgoing_quantity: number
  average_monthly_usage: number
  months_of_coverage: number | null
  suggested_order_quantity: number
  risk: string
}

export type StockShortageRisksResponse = {
  lookback_days: number
  total_at_risk: number
  items: StockShortageRisk[]
}

export type ChatSource = {
  reference: string | null
  final_score: number
  reranker_score: number
  dense_score: number
  classification: string | null
  equipment_code: string | null
  equipment_brand: string | null
  equipment_model: string | null
  link_trust: string | null
}

export type ChatResponse = {
  answer: string
  summary: string
  probable_causes: string[]
  recommended_checks: string[]
  historical_solutions: string[]
  warnings: string[]
  confidence: "HIGH" | "MEDIUM" | "LOW"
  confidence_score: number
  human_validation_required: boolean
  intent: string
  classification_group: string | null
  equipment_code: string | null
  model: string
  llm_used: boolean
  sources: ChatSource[]
}

export type PreventivePlan = {
  id: number
  equipment_id: number
  title: string
  description: string | null
  frequency_days: number
  priority: string
  assigned_technician_id: number | null
  active: boolean
  next_due_date: string
  last_executed_at: string | null
  created_by_id: number
  created_at: string
  updated_at: string
}

export type PreventiveExecution = {
  id: number
  plan_id: number
  intervention_id: number
  scheduled_date: string
  triggered_at: string
  status: string
  notes: string | null
  triggered_by_id: number
  created_at: string
  updated_at: string
}

export type MaintenanceKpi = {
  period_start: string
  period_end: string
  total_interventions: number
  completed_interventions: number
  corrective_interventions: number
  preventive_interventions: number
  preventive_ratio_percent: number
  mttr_hours: number | null
  mtbf_hours: number | null
  estimated_availability_percent: number | null
  total_actual_cost: number
  active_preventive_plans: number
  due_preventive_plans: number
  overdue_preventive_plans: number
}

export type EquipmentKpi = {
  equipment_id: number
  equipment_code: string
  total_interventions: number
  completed_interventions: number
  corrective_interventions: number
  preventive_interventions: number
  mttr_hours: number | null
  mtbf_hours: number | null
  total_actual_cost: number
  last_intervention_at: string | null
  next_preventive_due_date: string | null
  active_preventive_plans: number
}

export type MonthlyReportMetrics = {
  year: number
  month: number
  period_start: string
  period_end: string
  submitted_requests: number
  resolved_requests: number
  created_interventions: number
  completed_interventions: number
  corrective_interventions: number
  preventive_interventions: number
  mttr_hours: number | null
  total_actual_cost: number
  current_equipment_failures: number
  current_low_stock_parts: number
  due_preventive_plans: number
  overdue_preventive_plans: number
}

export type MonthlyReport = {
  metrics: MonthlyReportMetrics
  summary: string
  llm_used: boolean
  model_name: string | null
}

export type GeneratedReport = {
  id: number
  report_type: string
  period_start: string
  period_end: string
  metrics: Record<string, unknown>
  summary: string
  llm_used: boolean
  model_name: string | null
  generated_by_id: number
  created_at: string
  updated_at: string
}

export type FailureForecast = {
  id: number
  equipment_id: number
  forecasted_at: string
  horizon_days: number
  risk_score: number
  failure_probability: number
  probability_calibrated: boolean
  risk_level: string
  evidence_confidence: string
  predicted_failure_family: string | null
  estimated_start_date: string | null
  estimated_end_date: string | null
  factors: string[]
  recommended_actions: string[]
  evidence_summary: Record<string, unknown>
  similar_references: string[]
  explanation: string
  methodology_version: string
  llm_used: boolean
  model_name: string | null
  recommendation_id: number | null
  notification_created: boolean
  validation_status: string
  validated_by_id: number | null
  validated_at: string | null
  validation_notes: string | null
  actual_failure_occurred: boolean | null
  actual_failure_date: string | null
  created_by_id: number | null
  created_at: string
  updated_at: string
}

export type FailureForecastRun = {
  id: number
  started_at: string
  ended_at: string | null
  status: string
  horizon_days: number
  only_with_history: boolean
  requested_limit: number
  processed_count: number
  high_risk_count: number
  medium_risk_count: number
  low_risk_count: number
  notifications_created: number
  recommendations_created: number
  error_count: number
  error_details: unknown[]
  triggered_by_id: number | null
  created_at: string
  updated_at: string
}

export type FailureForecastSummary = {
  total_forecasts: number
  latest_forecasts: number
  high_risk: number
  medium_risk: number
  low_risk: number
  pending_validation: number
  confirmed: number
  partial: number
  rejected: number
  latest_run: FailureForecastRun | null
  warning: string
}

export type FailureForecastBatchResponse = {
  run_id: number
  status: string
  horizon_days: number
  processed_count: number
  high_risk_count: number
  medium_risk_count: number
  low_risk_count: number
  notifications_created: number
  recommendations_created: number
  error_count: number
}

export type AuditLog = {
  id: number
  actor_id: number | null
  action: string
  entity_type: string
  entity_id: string | null
  details: Record<string, unknown> | null
  occurred_at: string
}
