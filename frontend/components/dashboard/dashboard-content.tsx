"use client"

import {
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  BrainCircuit,
  CheckCircle2,
  ClipboardList,
  Gauge,
  PackageOpen,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Timer,
  Wrench,
} from "lucide-react"
import Link from "next/link"
import { useEffect, useState } from "react"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { StatusBadge } from "@/components/common/status-badge"
import { Header } from "@/components/dashboard/header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ApiError, apiFetch } from "@/lib/api"
import { formatDate, formatDateTime, formatHours, formatMoney } from "@/lib/format"
import type {
  DashboardSummary,
  FailureForecast,
  FailureForecastSummary,
  Intervention,
  MaintenanceKpi,
  MaintenanceRequest,
  PreventivePlan,
  Recommendation,
  StockSummary,
} from "@/lib/types"

const emptyDashboard: DashboardSummary = {
  total_equipments: 0,
  equipments_in_service: 0,
  equipments_in_failure: 0,
  open_requests: 0,
  active_interventions: 0,
  low_stock_parts: 0,
  open_recommendations: 0,
  average_repair_hours: null,
}

const emptyForecast: FailureForecastSummary = {
  total_forecasts: 0,
  latest_forecasts: 0,
  high_risk: 0,
  medium_risk: 0,
  low_risk: 0,
  pending_validation: 0,
  confirmed: 0,
  partial: 0,
  rejected: 0,
  latest_run: null,
  warning: "",
}

export function DashboardContent() {
  const [dashboard, setDashboard] = useState<DashboardSummary>(emptyDashboard)
  const [stock, setStock] = useState<StockSummary | null>(null)
  const [kpi, setKpi] = useState<MaintenanceKpi | null>(null)
  const [forecastSummary, setForecastSummary] = useState<FailureForecastSummary>(emptyForecast)
  const [highRisks, setHighRisks] = useState<FailureForecast[]>([])
  const [duePlans, setDuePlans] = useState<PreventivePlan[]>([])
  const [requests, setRequests] = useState<MaintenanceRequest[]>([])
  const [interventions, setInterventions] = useState<Intervention[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [dashboardData, stockData, kpiData, forecastData, riskData, planData, requestData, interventionData, recommendationData] = await Promise.all([
        apiFetch<DashboardSummary>("/dashboard/summary"),
        apiFetch<StockSummary>("/stock/summary"),
        apiFetch<MaintenanceKpi>("/kpi/maintenance?months=12"),
        apiFetch<FailureForecastSummary>("/ai/failure-forecasts/summary"),
        apiFetch<FailureForecast[]>("/ai/failure-forecasts/high-risk?limit=8"),
        apiFetch<PreventivePlan[]>("/preventive-maintenance/due?days_ahead=30&limit=8"),
        apiFetch<MaintenanceRequest[]>("/maintenance-requests?limit=6"),
        apiFetch<Intervention[]>("/interventions?limit=6"),
        apiFetch<Recommendation[]>("/recommendations?limit=6"),
      ])
      setDashboard(dashboardData)
      setStock(stockData)
      setKpi(kpiData)
      setForecastSummary(forecastData)
      setHighRisks(riskData)
      setDuePlans(planData)
      setRequests(requestData)
      setInterventions(interventionData)
      setRecommendations(recommendationData)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger le tableau de bord.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [])

  const serviceRate = dashboard.total_equipments > 0 ? (dashboard.equipments_in_service / dashboard.total_equipments) * 100 : 0
  const preventiveRatio = kpi?.preventive_ratio_percent ?? 0

  return (
    <>
      <Header
        title="Centre de pilotage MaintIA"
        description="Vue consolidée du parc, de l’atelier, du préventif, du stock et des risques prédictifs."
        actions={<><Button asChild className="h-9"><Link href="/forecasts"><BrainCircuit className="mr-2 h-4 w-4" />Analyser les risques</Link></Button><Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button></>}
      />

      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        {loading ? <LoadingState /> : (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard label="Parc informatique" value={dashboard.total_equipments.toLocaleString("fr-FR")} helper={`${dashboard.equipments_in_service.toLocaleString("fr-FR")} en service`} icon={Boxes} />
              <KpiCard label="Demandes ouvertes" value={String(dashboard.open_requests)} helper="À traiter ou en cours" icon={ClipboardList} tone="blue" />
              <KpiCard label="Interventions actives" value={String(dashboard.active_interventions)} helper={`${interventions.filter((item) => item.status === "COMPLETED").length} récemment terminée(s)`} icon={Wrench} tone="purple" />
              <KpiCard label="Risques élevés" value={String(forecastSummary.high_risk)} helper={`${forecastSummary.pending_validation} prévision(s) à valider`} icon={AlertTriangle} tone="red" />
            </div>

            <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <Card className="overflow-hidden border-primary/15 bg-gradient-to-br from-card to-primary/[0.035] shadow-sm">
                <div className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary"><Gauge className="h-3.5 w-3.5" />Santé opérationnelle</div>
                      <h2 className="text-xl font-bold">Disponibilité et maintenance</h2>
                      <p className="text-xs text-muted-foreground">Indicateurs calculés sur les 12 derniers mois.</p>
                    </div>
                    <Button asChild size="sm" variant="outline"><Link href="/reports">Voir les KPI <ArrowUpRight className="ml-1 h-3.5 w-3.5" /></Link></Button>
                  </div>
                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    <GaugeMetric label="Équipements en service" value={serviceRate} display={`${serviceRate.toFixed(1)}%`} />
                    <GaugeMetric label="Part du préventif" value={preventiveRatio} display={`${preventiveRatio.toFixed(1)}%`} />
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
                    <MiniMetric label="MTTR" value={formatHours(kpi?.mttr_hours)} icon={Timer} />
                    <MiniMetric label="MTBF" value={formatHours(kpi?.mtbf_hours)} icon={ShieldCheck} />
                    <MiniMetric label="Coût réel" value={formatMoney(kpi?.total_actual_cost ?? 0)} icon={Sparkles} />
                    <MiniMetric label="Plans en retard" value={String(kpi?.overdue_preventive_plans ?? 0)} icon={Stethoscope} danger={(kpi?.overdue_preventive_plans ?? 0) > 0} />
                  </div>
                </div>
              </Card>

              <Card className="overflow-hidden shadow-sm">
                <div className="border-b p-5"><div className="flex items-center justify-between"><div><h2 className="font-semibold">Stock critique</h2><p className="text-xs text-muted-foreground">État physique et valorisation.</p></div><Button asChild size="sm" variant="ghost"><Link href="/stock">Ouvrir</Link></Button></div></div>
                <div className="grid grid-cols-2 gap-3 p-5">
                  <MiniNumber label="Références actives" value={stock?.active_parts ?? 0} />
                  <MiniNumber label="Quantité totale" value={stock?.total_quantity ?? 0} />
                  <MiniNumber label="Stock faible" value={stock?.low_stock_parts ?? 0} danger={(stock?.low_stock_parts ?? 0) > 0} />
                  <MiniNumber label="Ruptures" value={stock?.out_of_stock_parts ?? 0} danger={(stock?.out_of_stock_parts ?? 0) > 0} />
                </div>
                <div className="border-t bg-secondary/20 p-4"><p className="text-xs text-muted-foreground">Valeur d’inventaire</p><p className="mt-1 text-2xl font-black">{formatMoney(stock?.inventory_value ?? 0)}</p></div>
              </Card>
            </div>

            <div className="grid gap-4 xl:grid-cols-2">
              <DashboardTable title="Dernières demandes" href="/requests" headers={["Référence", "Priorité", "Statut", "Date"]} rows={requests.map((item) => [<span key="ref" className="font-semibold">{item.reference}</span>, <StatusBadge key="priority" value={item.priority} />, <StatusBadge key="status" value={item.status} />, formatDateTime(item.submitted_at)])} empty="Aucune nouvelle demande." />
              <DashboardTable title="Interventions récentes" href="/interventions" headers={["Référence", "Type", "Statut", "Coût"]} rows={interventions.map((item) => [<span key="ref" className="font-semibold">{item.reference}</span>, <StatusBadge key="type" value={item.maintenance_type} />, <StatusBadge key="status" value={item.status} />, formatMoney(item.actual_cost)])} empty="Aucune intervention récente." />
            </div>

            <div className="grid gap-4 xl:grid-cols-3">
              <ListCard title="Échéances préventives" href="/preventive" icon={Stethoscope} items={duePlans.map((item) => ({ title: item.title, meta: `Équipement #${item.equipment_id} · ${formatDate(item.next_due_date)}`, status: item.priority }))} empty="Aucune échéance à 30 jours." />
              <ListCard title="Risques prédictifs HIGH" href="/forecasts" icon={AlertTriangle} items={highRisks.map((item) => ({ title: `Équipement #${item.equipment_id}`, meta: `${item.risk_score}/100 · ${item.predicted_failure_family ?? "Famille inconnue"}`, status: item.validation_status }))} empty="Aucun risque HIGH détecté." />
              <ListCard title="Recommandations" href="/recommendations" icon={Sparkles} items={recommendations.map((item) => ({ title: item.title, meta: item.recommended_action, status: item.risk_level }))} empty="Aucune recommandation ouverte." />
            </div>
          </>
        )}
      </div>
    </>
  )
}

function KpiCard({ label, value, helper, icon: Icon, tone = "primary" }: { label: string; value: string; helper: string; icon: typeof Boxes; tone?: "primary" | "blue" | "purple" | "red" }) {
  const tones = { primary: "bg-primary/10 text-primary", blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/30", purple: "bg-violet-50 text-violet-600 dark:bg-violet-950/30", red: "bg-red-50 text-red-600 dark:bg-red-950/30" }
  return <Card className="p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg"><div className="flex items-start justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-black tracking-tight">{value}</p><p className="mt-1 text-[10px] text-muted-foreground">{helper}</p></div><div className={`rounded-2xl p-3 ${tones[tone]}`}><Icon className="h-5 w-5" /></div></div></Card>
}

function GaugeMetric({ label, value, display }: { label: string; value: number; display: string }) { return <div className="rounded-2xl border bg-card/80 p-4"><div className="flex items-end justify-between"><p className="text-xs text-muted-foreground">{label}</p><p className="text-2xl font-black">{display}</p></div><Progress value={Math.max(0, Math.min(100, value))} className="mt-3" /></div> }
function MiniMetric({ label, value, icon: Icon, danger = false }: { label: string; value: string; icon: typeof Timer; danger?: boolean }) { return <div className={`rounded-2xl border p-3 ${danger ? "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/20" : "bg-card/80"}`}><Icon className={`h-4 w-4 ${danger ? "text-red-600" : "text-primary"}`} /><p className="mt-3 text-[10px] text-muted-foreground">{label}</p><p className="mt-1 text-sm font-bold">{value}</p></div> }
function MiniNumber({ label, value, danger = false }: { label: string; value: number; danger?: boolean }) { return <div className={`rounded-2xl border p-4 ${danger ? "border-red-200 bg-red-50/70 dark:border-red-900 dark:bg-red-950/20" : "bg-secondary/20"}`}><p className="text-[10px] text-muted-foreground">{label}</p><p className={`mt-1 text-2xl font-black ${danger ? "text-red-600" : ""}`}>{value.toLocaleString("fr-FR")}</p></div> }

function DashboardTable({ title, href, headers, rows, empty }: { title: string; href: string; headers: string[]; rows: React.ReactNode[][]; empty: string }) {
  return <Card className="overflow-hidden shadow-sm"><div className="flex items-center justify-between border-b p-4"><h2 className="font-semibold">{title}</h2><Button asChild variant="ghost" size="sm"><Link href={href}>Voir tout <ArrowUpRight className="ml-1 h-3.5 w-3.5" /></Link></Button></div>{rows.length === 0 ? <p className="p-5 text-sm text-muted-foreground">{empty}</p> : <div className="overflow-x-auto"><Table><TableHeader><TableRow>{headers.map((item) => <TableHead key={item}>{item}</TableHead>)}</TableRow></TableHeader><TableBody>{rows.map((row, index) => <TableRow key={index}>{row.map((cell, cellIndex) => <TableCell key={cellIndex}>{cell}</TableCell>)}</TableRow>)}</TableBody></Table></div>}</Card>
}

function ListCard({ title, href, icon: Icon, items, empty }: { title: string; href: string; icon: typeof Sparkles; items: Array<{ title: string; meta: string; status: string }>; empty: string }) {
  return <Card className="overflow-hidden shadow-sm"><div className="flex items-center justify-between border-b p-4"><div className="flex items-center gap-2"><Icon className="h-4 w-4 text-primary" /><h2 className="font-semibold">{title}</h2></div><Button asChild variant="ghost" size="sm"><Link href={href}>Ouvrir</Link></Button></div><div className="space-y-2 p-4">{items.length === 0 ? <div className="flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-xs text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-200"><CheckCircle2 className="h-4 w-4" />{empty}</div> : items.slice(0, 5).map((item, index) => <div key={`${item.title}-${index}`} className="rounded-xl border p-3"><div className="flex items-start justify-between gap-2"><p className="text-sm font-semibold">{item.title}</p><StatusBadge value={item.status} /></div><p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{item.meta}</p></div>)}</div></Card>
}
