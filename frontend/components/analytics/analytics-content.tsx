"use client"

import { BarChart3, Boxes, Clock3, PackageOpen, RefreshCcw, TrendingUp, Wrench } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { Header } from "@/components/dashboard/header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { apiFetch, ApiError } from "@/lib/api"
import { formatHours, formatMoney } from "@/lib/format"
import { statusLabel } from "@/lib/status"
import type { DashboardSummary, Equipment, Intervention, MaintenanceRequest, SparePart } from "@/lib/types"

const chartColors = ["var(--color-chart-1)", "var(--color-chart-2)", "var(--color-chart-3)", "var(--color-chart-4)", "var(--color-chart-5)"]

export function AnalyticsContent() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [equipments, setEquipments] = useState<Equipment[]>([])
  const [requests, setRequests] = useState<MaintenanceRequest[]>([])
  const [interventions, setInterventions] = useState<Intervention[]>([])
  const [parts, setParts] = useState<SparePart[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, equipmentData, requestData, interventionData, partData] = await Promise.all([
        apiFetch<DashboardSummary>("/dashboard/summary"),
        apiFetch<Equipment[]>("/equipments?limit=200"),
        apiFetch<MaintenanceRequest[]>("/maintenance-requests?limit=200"),
        apiFetch<Intervention[]>("/interventions?limit=200"),
        apiFetch<SparePart[]>("/spare-parts?limit=200"),
      ])
      setSummary(summaryData)
      setEquipments(equipmentData)
      setRequests(requestData)
      setInterventions(interventionData)
      setParts(partData)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les indicateurs.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [])

  const equipmentStatusData = useMemo(() => groupBy(equipments.map((item) => item.status)), [equipments])
  const requestPriorityData = useMemo(() => groupBy(requests.map((item) => item.priority)), [requests])
  const interventionStatusData = useMemo(() => groupBy(interventions.map((item) => item.status)), [interventions])
  const maintenanceTypeData = useMemo(() => groupBy(interventions.map((item) => item.maintenance_type)), [interventions])
  const totalMaintenanceCost = useMemo(() => interventions.reduce((sum, item) => sum + Number(item.actual_cost || 0), 0), [interventions])
  const lowStockRate = useMemo(() => parts.length ? Math.round((parts.filter((item) => item.quantity <= item.minimum_threshold).length / parts.length) * 100) : 0, [parts])

  return (
    <>
      <Header title="Analytique opérationnelle" description="Analysez la disponibilité du parc, la charge de maintenance, les priorités et le risque de rupture du stock." actions={<Button variant="outline" className="h-9 bg-transparent" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button>} />
      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        {loading ? <LoadingState /> : !summary ? <EmptyState title="Aucune donnée" description="Les indicateurs seront disponibles après la création des premières données." icon={BarChart3} /> : (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi label="Disponibilité du parc" value={summary.total_equipments ? `${Math.round((summary.equipments_in_service / summary.total_equipments) * 100)}%` : "0%"} helper={`${summary.equipments_in_service} sur ${summary.total_equipments} en service`} icon={Boxes} />
              <Kpi label="MTTR" value={formatHours(summary.average_repair_hours)} helper="Durée moyenne de réparation" icon={Clock3} tone="blue" />
              <Kpi label="Coût maintenance" value={formatMoney(totalMaintenanceCost)} helper={`${interventions.length} intervention(s) analysée(s)`} icon={Wrench} tone="purple" />
              <Kpi label="Risque de stock" value={`${lowStockRate}%`} helper={`${summary.low_stock_parts} référence(s) au seuil`} icon={PackageOpen} tone="amber" />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <ChartCard title="État du parc" description="Répartition des équipements par état">
                <ResponsiveContainer width="100%" height={290}>
                  <BarChart data={equipmentStatusData} margin={{ top: 10, right: 10, left: -20, bottom: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.25} />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-18} textAnchor="end" height={55} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", background: "var(--card)" }} />
                    <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="var(--color-chart-1)" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Priorité des demandes" description="Répartition des signalements par niveau de criticité">
                {requestPriorityData.length ? (
                  <div className="grid items-center gap-4 sm:grid-cols-[1fr_0.9fr]">
                    <ResponsiveContainer width="100%" height={290}>
                      <PieChart><Pie data={requestPriorityData} dataKey="value" nameKey="name" innerRadius={62} outerRadius={96} paddingAngle={4}>{requestPriorityData.map((entry, index) => <Cell key={entry.key} fill={chartColors[index % chartColors.length]} />)}</Pie><Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", background: "var(--card)" }} /></PieChart>
                    </ResponsiveContainer>
                    <div className="space-y-2">{requestPriorityData.map((item, index) => <div key={item.key} className="flex items-center justify-between rounded-xl bg-secondary/60 p-3"><div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: chartColors[index % chartColors.length] }} /><span className="text-xs">{item.name}</span></div><span className="text-sm font-bold">{item.value}</span></div>)}</div>
                  </div>
                ) : <EmptyState title="Pas encore de demandes" description="La répartition apparaîtra dès qu’une demande sera créée." icon={TrendingUp} />}
              </ChartCard>

              <ChartCard title="Avancement des interventions" description="Nombre d’interventions dans chaque étape du cycle">
                <ResponsiveContainer width="100%" height={290}>
                  <BarChart data={interventionStatusData} layout="vertical" margin={{ top: 5, right: 20, left: 25, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.25} />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 10 }} />
                    <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", background: "var(--card)" }} />
                    <Bar dataKey="value" radius={[0, 8, 8, 0]} fill="var(--color-chart-2)" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Type de maintenance" description="Équilibre entre maintenance corrective et préventive">
                {maintenanceTypeData.length ? <div className="grid gap-4 sm:grid-cols-2">{maintenanceTypeData.map((item, index) => <div key={item.key} className="rounded-2xl border border-border/80 p-5"><div className="mb-5 flex items-center justify-between"><div className="rounded-xl p-3" style={{ backgroundColor: `color-mix(in oklch, ${chartColors[index % chartColors.length]} 15%, transparent)`, color: chartColors[index % chartColors.length] }}><Wrench className="h-5 w-5" /></div><span className="text-4xl font-bold">{item.value}</span></div><p className="font-semibold">{item.name}</p><p className="mt-1 text-xs text-muted-foreground">{interventions.length ? Math.round((item.value / interventions.length) * 100) : 0}% des interventions</p></div>)}</div> : <EmptyState title="Pas encore d’interventions" description="Les types de maintenance seront analysés ici." icon={Wrench} />}
              </ChartCard>
            </div>

            <Card className="border-border/80 bg-card p-5 shadow-sm">
              <div className="flex items-start gap-3"><div className="rounded-xl bg-primary/10 p-3 text-primary"><TrendingUp className="h-5 w-5" /></div><div><h2 className="font-semibold">Périmètre de cette page</h2><p className="mt-1 text-sm leading-relaxed text-muted-foreground">Ces graphiques sont calculés à partir des données opérationnelles disponibles dans l’API. Après l’import et le nettoyage de l’historique Excel, les analyses avancées, tendances mensuelles, MTBF, coûts cumulés, pannes par marque et prévisions seront alimentées depuis PostgreSQL et Power BI.</p></div></div>
            </Card>
          </>
        )}
      </div>
    </>
  )
}

function groupBy(values: string[]) {
  const counts = new Map<string, number>()
  for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1)
  return [...counts.entries()].map(([key, value]) => ({ key, name: statusLabel(key), value }))
}

function Kpi({ label, value, helper, icon: Icon, tone = "primary" }: { label: string; value: string; helper: string; icon: typeof Boxes; tone?: "primary" | "blue" | "purple" | "amber" }) {
  const color = tone === "blue" ? "bg-blue-50 text-blue-600 dark:bg-blue-950/30" : tone === "purple" ? "bg-violet-50 text-violet-600 dark:bg-violet-950/30" : tone === "amber" ? "bg-amber-50 text-amber-600 dark:bg-amber-950/30" : "bg-primary/10 text-primary"
  return <Card className="p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg"><div className="flex items-start justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p><p className="mt-1 text-[10px] text-muted-foreground">{helper}</p></div><div className={`rounded-xl p-3 ${color}`}><Icon className="h-5 w-5" /></div></div></Card>
}

function ChartCard({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <Card className="overflow-hidden border-border/80 bg-card shadow-sm"><div className="border-b border-border/70 p-5"><h2 className="font-semibold">{title}</h2><p className="text-xs text-muted-foreground">{description}</p></div><div className="p-5">{children}</div></Card>
}
