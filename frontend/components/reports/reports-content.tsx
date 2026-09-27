"use client"

import { BarChart3, Bot, CalendarRange, Download, FileText, Gauge, Printer, RefreshCcw, Sparkles, Timer, Wrench } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useAuth } from "@/components/auth/auth-provider"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { StatusBadge } from "@/components/common/status-badge"
import { Header } from "@/components/dashboard/header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ApiError, apiFetch, buildQuery } from "@/lib/api"
import { formatDate, formatDateTime, formatHours, formatMoney } from "@/lib/format"
import { hasRole, permissions } from "@/lib/permissions"
import type { GeneratedReport, MaintenanceKpi, MonthlyReport } from "@/lib/types"

const now = new Date()

export function ReportsContent() {
  const { user } = useAuth()
  const canGenerate = hasRole(user?.role, permissions.manager)
  const [kpi, setKpi] = useState<MaintenanceKpi | null>(null)
  const [reports, setReports] = useState<GeneratedReport[]>([])
  const [monthly, setMonthly] = useState<MonthlyReport | null>(null)
  const [months, setMonths] = useState("12")
  const [year, setYear] = useState(String(now.getFullYear()))
  const [month, setMonth] = useState(String(now.getMonth() + 1))
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [kpiData, reportData] = await Promise.all([
        apiFetch<MaintenanceKpi>(`/kpi/maintenance?months=${months}`),
        apiFetch<GeneratedReport[]>("/reports?limit=100"),
      ])
      setKpi(kpiData)
      setReports(reportData)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les KPI et rapports.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [months])

  async function previewMonthly() {
    setWorking(true)
    try {
      const data = await apiFetch<MonthlyReport>(`/reports/monthly${buildQuery({ year: Number(year), month: Number(month) })}`)
      setMonthly(data)
      toast.success("Rapport calculé")
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Calcul impossible.")
    } finally {
      setWorking(false)
    }
  }

  async function generateMonthly() {
    if (!canGenerate) return
    setWorking(true)
    try {
      const data = await apiFetch<MonthlyReport>(`/reports/monthly/generate${buildQuery({ year: Number(year), month: Number(month) })}`, { method: "POST", timeoutMs: 120_000 })
      setMonthly(data)
      toast.success(data.llm_used ? "Rapport généré avec MaintIA" : "Rapport généré avec le moteur déterministe")
      await loadData()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Génération impossible.")
    } finally {
      setWorking(false)
    }
  }

  function downloadJson() {
    if (!monthly) return
    const blob = new Blob([JSON.stringify(monthly, null, 2)], { type: "application/json;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = `rapport-maintia-${year}-${month.padStart(2, "0")}.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <Header
        title="KPI et rapports"
        description="Suivez la performance de l’atelier, le préventif, les coûts et les rapports mensuels expliqués par MaintIA."
        actions={<Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button>}
      />
      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        {loading ? <LoadingState /> : (
          <Tabs defaultValue="kpi" className="space-y-4">
            <TabsList><TabsTrigger value="kpi">KPI atelier</TabsTrigger><TabsTrigger value="monthly">Rapport mensuel</TabsTrigger><TabsTrigger value="archive">Rapports générés</TabsTrigger></TabsList>

            <TabsContent value="kpi" className="space-y-4">
              <Card className="p-4 shadow-sm"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold">Période analysée</h2><p className="text-xs text-muted-foreground">{formatDate(kpi?.period_start)} → {formatDate(kpi?.period_end)}</p></div><div className="w-40"><Label className="text-xs">Période</Label><select className="mt-1 h-9 w-full rounded-lg border bg-card px-3 text-sm" value={months} onChange={(event) => setMonths(event.target.value)}><option value="3">3 mois</option><option value="6">6 mois</option><option value="12">12 mois</option><option value="24">24 mois</option></select></div></div></Card>
              {kpi && <><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Kpi label="Interventions" value={String(kpi.total_interventions)} helper={`${kpi.completed_interventions} terminées`} icon={Wrench} /><Kpi label="MTTR" value={formatHours(kpi.mttr_hours)} helper="Temps moyen de réparation" icon={Timer} tone="blue" /><Kpi label="MTBF" value={formatHours(kpi.mtbf_hours)} helper="Temps moyen entre pannes" icon={Gauge} tone="purple" /><Kpi label="Coût réel" value={formatMoney(kpi.total_actual_cost)} helper="Période analysée" icon={BarChart3} tone="amber" /></div><div className="grid gap-4 lg:grid-cols-2"><Card className="p-5 shadow-sm"><h2 className="font-semibold">Équilibre préventif / correctif</h2><p className="text-xs text-muted-foreground">Part des interventions préventives.</p><div className="mt-6 flex items-end justify-between"><p className="text-4xl font-black">{kpi.preventive_ratio_percent.toFixed(1)}%</p><p className="text-xs text-muted-foreground">{kpi.preventive_interventions} préventives · {kpi.corrective_interventions} correctives</p></div><Progress className="mt-4" value={kpi.preventive_ratio_percent} /></Card><Card className="p-5 shadow-sm"><h2 className="font-semibold">État du préventif</h2><div className="mt-4 grid grid-cols-3 gap-3 text-center"><Metric label="Actifs" value={kpi.active_preventive_plans} /><Metric label="À échéance" value={kpi.due_preventive_plans} /><Metric label="En retard" value={kpi.overdue_preventive_plans} danger={kpi.overdue_preventive_plans > 0} /></div><div className="mt-5 rounded-xl bg-primary/5 p-3 text-xs text-muted-foreground">Disponibilité estimée : <b className="text-foreground">{kpi.estimated_availability_percent === null ? "Non calculable" : `${kpi.estimated_availability_percent.toFixed(2)}%`}</b></div></Card></div></>}
            </TabsContent>

            <TabsContent value="monthly" className="space-y-4">
              <Card className="p-5 shadow-sm"><div className="flex items-start gap-3"><div className="rounded-2xl bg-primary/10 p-3 text-primary"><CalendarRange className="h-5 w-5" /></div><div><h2 className="font-semibold">Générer le rapport mensuel</h2><p className="text-xs text-muted-foreground">Les métriques sont calculées par PostgreSQL. Le LLM rédige uniquement la synthèse.</p></div></div><div className="mt-5 grid gap-4 sm:grid-cols-[160px_160px_1fr]"><Field label="Année"><Input type="number" min="2000" max="2100" value={year} onChange={(event) => setYear(event.target.value)} /></Field><Field label="Mois"><Input type="number" min="1" max="12" value={month} onChange={(event) => setMonth(event.target.value)} /></Field><div className="flex flex-wrap items-end gap-2"><Button variant="outline" onClick={() => void previewMonthly()} disabled={working}><FileText className="mr-2 h-4 w-4" />Prévisualiser</Button><Button onClick={() => void generateMonthly()} disabled={!canGenerate || working}><Sparkles className="mr-2 h-4 w-4" />Générer et conserver</Button></div></div></Card>
              {monthly ? <Card className="overflow-hidden shadow-sm print:border-0 print:shadow-none"><div className="border-b bg-primary/[0.035] p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-bold">Rapport mensuel · {monthly.metrics.month.toString().padStart(2, "0")}/{monthly.metrics.year}</h2><p className="text-xs text-muted-foreground">{formatDate(monthly.metrics.period_start)} → {formatDate(monthly.metrics.period_end)}</p></div><div className="flex gap-2"><StatusBadge value={monthly.llm_used ? "LLM" : "DETERMINISTIC"} /><Button size="sm" variant="outline" onClick={downloadJson}><Download className="mr-1 h-3.5 w-3.5" />JSON</Button><Button size="sm" variant="outline" onClick={() => window.print()}><Printer className="mr-1 h-3.5 w-3.5" />Imprimer / PDF</Button></div></div></div><div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Demandes soumises" value={monthly.metrics.submitted_requests} /><Metric label="Demandes résolues" value={monthly.metrics.resolved_requests} /><Metric label="Interventions créées" value={monthly.metrics.created_interventions} /><Metric label="Interventions terminées" value={monthly.metrics.completed_interventions} /><Metric label="Équipements en panne" value={monthly.metrics.current_equipment_failures} danger={monthly.metrics.current_equipment_failures > 0} /><Metric label="Stock faible" value={monthly.metrics.current_low_stock_parts} danger={monthly.metrics.current_low_stock_parts > 0} /><Metric label="Préventif dû" value={monthly.metrics.due_preventive_plans} /><Metric label="Préventif en retard" value={monthly.metrics.overdue_preventive_plans} danger={monthly.metrics.overdue_preventive_plans > 0} /></div><div className="border-t p-5"><div className="mb-3 flex items-center gap-2"><Bot className="h-4 w-4 text-primary" /><h3 className="font-semibold">Synthèse</h3></div><p className="whitespace-pre-line text-sm leading-7 text-muted-foreground">{monthly.summary}</p><p className="mt-4 text-[10px] text-muted-foreground">Moteur : {monthly.model_name ?? "Déterministe"}</p></div></Card> : <EmptyState title="Aucun rapport affiché" description="Choisissez une période puis prévisualisez ou générez le rapport." icon={FileText} />}
            </TabsContent>

            <TabsContent value="archive"><Card className="overflow-hidden shadow-sm">{reports.length === 0 ? <div className="p-5"><EmptyState title="Aucun rapport généré" description="Les rapports persistés apparaîtront ici." icon={FileText} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Rapport</TableHead><TableHead>Période</TableHead><TableHead>Moteur</TableHead><TableHead>Généré le</TableHead><TableHead>Synthèse</TableHead></TableRow></TableHeader><TableBody>{reports.map((item) => <TableRow key={item.id}><TableCell className="font-semibold">#{item.id} · {item.report_type}</TableCell><TableCell>{formatDate(item.period_start)} → {formatDate(item.period_end)}</TableCell><TableCell><StatusBadge value={item.llm_used ? "LLM" : "DETERMINISTIC"} /></TableCell><TableCell>{formatDateTime(item.created_at)}</TableCell><TableCell className="max-w-xl"><p className="line-clamp-3 text-sm text-muted-foreground">{item.summary}</p></TableCell></TableRow>)}</TableBody></Table></div>}</Card></TabsContent>
          </Tabs>
        )}
      </div>
    </>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }
function Metric({ label, value, danger = false }: { label: string; value: number | string; danger?: boolean }) { return <div className={`rounded-2xl border p-4 ${danger ? "border-red-200 bg-red-50/60 dark:border-red-900 dark:bg-red-950/20" : "bg-card"}`}><p className="text-[11px] text-muted-foreground">{label}</p><p className={`mt-1 text-2xl font-black ${danger ? "text-red-600" : ""}`}>{value}</p></div> }
function Kpi({ label, value, helper, icon: Icon, tone = "primary" }: { label: string; value: string; helper: string; icon: typeof Wrench; tone?: "primary" | "blue" | "purple" | "amber" }) { const colors = { primary: "bg-primary/10 text-primary", blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/30", purple: "bg-violet-50 text-violet-600 dark:bg-violet-950/30", amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/30" }; return <Card className="p-4 shadow-sm"><div className="flex items-start justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-black">{value}</p><p className="mt-1 text-[10px] text-muted-foreground">{helper}</p></div><div className={`rounded-2xl p-3 ${colors[tone]}`}><Icon className="h-5 w-5" /></div></div></Card> }
