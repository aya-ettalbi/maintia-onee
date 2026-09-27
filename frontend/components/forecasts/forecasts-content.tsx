"use client"

import {
  AlertTriangle,
  BrainCircuit,
  CalendarClock,
  CheckCircle2,
  Gauge,
  History,
  LoaderCircle,
  Play,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { useAuth } from "@/components/auth/auth-provider"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { StatusBadge } from "@/components/common/status-badge"
import { Header } from "@/components/dashboard/header"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ApiError, apiFetch, buildQuery } from "@/lib/api"
import { formatDate, formatDateTime } from "@/lib/format"
import { hasRole, permissions } from "@/lib/permissions"
import type {
  Equipment,
  FailureForecast,
  FailureForecastBatchResponse,
  FailureForecastRun,
  FailureForecastSummary,
} from "@/lib/types"

const emptySummary: FailureForecastSummary = {
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

export function ForecastsContent() {
  const { user } = useAuth()
  const canBatch = hasRole(user?.role, permissions.manager)
  const canValidate = hasRole(user?.role, permissions.technician)
  const [summary, setSummary] = useState<FailureForecastSummary>(emptySummary)
  const [highRisk, setHighRisk] = useState<FailureForecast[]>([])
  const [runs, setRuns] = useState<FailureForecastRun[]>([])
  const [equipments, setEquipments] = useState<Equipment[]>([])
  const [selectedEquipment, setSelectedEquipment] = useState("")
  const [history, setHistory] = useState<FailureForecast[]>([])
  const [current, setCurrent] = useState<FailureForecast | null>(null)
  const [horizon, setHorizon] = useState("90")
  const [useLlm, setUseLlm] = useState(true)
  const [createActions, setCreateActions] = useState(false)
  const [batchLimit, setBatchLimit] = useState("100")
  const [batchActions, setBatchActions] = useState(false)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationOpen, setValidationOpen] = useState(false)
  const [validation, setValidation] = useState({ status: "CONFIRMED", notes: "", occurred: "UNKNOWN", date: "" })

  const equipmentMap = useMemo(() => new Map(equipments.map((item) => [item.id, item])), [equipments])

  async function loadOverview() {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, highRiskData, runData, equipmentData] = await Promise.all([
        apiFetch<FailureForecastSummary>("/ai/failure-forecasts/summary"),
        apiFetch<FailureForecast[]>("/ai/failure-forecasts/high-risk?limit=200"),
        apiFetch<FailureForecastRun[]>("/ai/failure-forecast-runs?limit=50"),
        apiFetch<Equipment[]>("/equipments?limit=200"),
      ])
      setSummary(summaryData)
      setHighRisk(highRiskData)
      setRuns(runData)
      setEquipments(equipmentData)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les prévisions.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadOverview() }, [])

  async function createForecast() {
    if (!selectedEquipment) return
    setWorking(true)
    try {
      const query = buildQuery({ horizon_days: Number(horizon), use_llm: useLlm, create_actions: createActions })
      const forecast = await apiFetch<FailureForecast>(`/ai/failure-forecasts/equipments/${selectedEquipment}${query}`, { method: "POST", timeoutMs: useLlm ? 120_000 : 45_000 })
      setCurrent(forecast)
      const forecastHistory = await apiFetch<FailureForecast[]>(`/ai/failure-forecasts/equipments/${selectedEquipment}/history?limit=50`)
      setHistory(forecastHistory)
      toast.success("Prévision calculée et enregistrée")
      await loadOverview()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Prévision impossible.")
    } finally {
      setWorking(false)
    }
  }

  async function loadEquipmentHistory(value = selectedEquipment) {
    if (!value) return
    setWorking(true)
    try {
      const forecastHistory = await apiFetch<FailureForecast[]>(`/ai/failure-forecasts/equipments/${value}/history?limit=50`)
      setHistory(forecastHistory)
      setCurrent(forecastHistory[0] ?? null)
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Historique indisponible.")
    } finally {
      setWorking(false)
    }
  }

  async function runBatch() {
    if (!canBatch) return
    setWorking(true)
    try {
      const result = await apiFetch<FailureForecastBatchResponse>("/ai/failure-forecasts/batch", {
        method: "POST",
        timeoutMs: 180_000,
        body: JSON.stringify({
          horizon_days: Number(horizon),
          limit: Number(batchLimit),
          offset: 0,
          only_with_history: true,
          create_actions: batchActions,
        }),
      })
      toast.success(`Batch terminé : ${result.processed_count} équipements, ${result.error_count} erreur(s)`)
      await loadOverview()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Batch impossible.")
    } finally {
      setWorking(false)
    }
  }

  function openValidation(item: FailureForecast) {
    setCurrent(item)
    setValidation({
      status: item.validation_status === "PENDING" ? "CONFIRMED" : item.validation_status,
      notes: item.validation_notes ?? "",
      occurred: item.actual_failure_occurred === null ? "UNKNOWN" : item.actual_failure_occurred ? "YES" : "NO",
      date: item.actual_failure_date ?? "",
    })
    setValidationOpen(true)
  }

  async function saveValidation() {
    if (!current) return
    setWorking(true)
    try {
      const updated = await apiFetch<FailureForecast>(`/ai/failure-forecasts/${current.id}/validate`, {
        method: "PATCH",
        body: JSON.stringify({
          validation_status: validation.status,
          notes: validation.notes || null,
          actual_failure_occurred: validation.occurred === "UNKNOWN" ? null : validation.occurred === "YES",
          actual_failure_date: validation.date || null,
        }),
      })
      setCurrent(updated)
      setHistory((items) => items.map((item) => item.id === updated.id ? updated : item))
      setHighRisk((items) => items.map((item) => item.id === updated.id ? updated : item))
      setValidationOpen(false)
      toast.success("Validation enregistrée")
      await loadOverview()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Validation impossible.")
    } finally {
      setWorking(false)
    }
  }

  return (
    <>
      <Header
        title="Prévisions de panne"
        description="Estimez le risque futur, expliquez les facteurs avec MaintIA et conservez la validation du technicien."
        actions={<Button variant="outline" className="h-9 bg-card" onClick={() => void loadOverview()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button>}
      />

      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        <Alert className="border-amber-200 bg-amber-50/80 text-amber-950 dark:border-amber-900 dark:bg-amber-950/25 dark:text-amber-100">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Estimation non calibrée</AlertTitle>
          <AlertDescription>{summary.warning || "Les probabilités sont heuristiques. Une validation humaine est obligatoire."}</AlertDescription>
        </Alert>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Kpi label="Prévisions" value={summary.total_forecasts} icon={Gauge} />
          <Kpi label="Risque élevé" value={summary.high_risk} icon={AlertTriangle} tone="red" />
          <Kpi label="Risque moyen" value={summary.medium_risk} icon={CalendarClock} tone="amber" />
          <Kpi label="À valider" value={summary.pending_validation} icon={ShieldCheck} tone="blue" />
          <Kpi label="Confirmées" value={summary.confirmed} icon={CheckCircle2} tone="green" />
        </div>

        {loading ? <LoadingState /> : (
          <Tabs defaultValue="forecast" className="space-y-4">
            <TabsList className="grid h-auto w-full grid-cols-2 gap-1 sm:w-auto sm:grid-cols-4">
              <TabsTrigger value="forecast">Prévision individuelle</TabsTrigger>
              <TabsTrigger value="risks">Risques élevés</TabsTrigger>
              <TabsTrigger value="batch">Batch</TabsTrigger>
              <TabsTrigger value="runs">Exécutions</TabsTrigger>
            </TabsList>

            <TabsContent value="forecast" className="space-y-4">
              <Card className="p-5 shadow-sm">
                <div className="grid gap-4 lg:grid-cols-[1fr_170px_1fr] lg:items-end">
                  <Field label="Équipement">
                    <Select value={selectedEquipment} onValueChange={(value) => { setSelectedEquipment(value); void loadEquipmentHistory(value) }}>
                      <SelectTrigger><SelectValue placeholder="Sélectionner un équipement" /></SelectTrigger>
                      <SelectContent>{equipments.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.code} · {[item.brand, item.model].filter(Boolean).join(" ")}</SelectItem>)}</SelectContent>
                    </Select>
                  </Field>
                  <Field label="Horizon">
                    <Select value={horizon} onValueChange={setHorizon}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="30">30 jours</SelectItem><SelectItem value="60">60 jours</SelectItem><SelectItem value="90">90 jours</SelectItem><SelectItem value="180">180 jours</SelectItem><SelectItem value="365">365 jours</SelectItem></SelectContent></Select>
                  </Field>
                  <div className="flex flex-wrap items-center gap-4 rounded-xl border bg-secondary/30 p-3">
                    <label className="flex items-center gap-2 text-xs"><Checkbox checked={useLlm} onCheckedChange={(value) => setUseLlm(Boolean(value))} />Explication OpenRouter</label>
                    {canBatch && <label className="flex items-center gap-2 text-xs"><Checkbox checked={createActions} onCheckedChange={(value) => setCreateActions(Boolean(value))} />Créer actions si HIGH</label>}
                    <Button onClick={() => void createForecast()} disabled={!selectedEquipment || working} className="ml-auto"><Sparkles className="mr-2 h-4 w-4" />{working ? "Calcul…" : "Calculer"}</Button>
                  </div>
                </div>
              </Card>

              {current ? <ForecastCard item={current} equipment={equipmentMap.get(current.equipment_id)} canValidate={canValidate} onValidate={() => openValidation(current)} /> : <EmptyState title="Aucune prévision sélectionnée" description="Choisissez un équipement puis lancez le calcul de risque." icon={BrainCircuit} />}

              {history.length > 0 && (
                <Card className="overflow-hidden shadow-sm">
                  <div className="border-b p-4"><h2 className="font-semibold">Historique de l’équipement</h2><p className="text-xs text-muted-foreground">Évolution des calculs et des validations.</p></div>
                  <ForecastTable items={history} equipmentMap={equipmentMap} canValidate={canValidate} onOpen={setCurrent} onValidate={openValidation} />
                </Card>
              )}
            </TabsContent>

            <TabsContent value="risks">
              <Card className="overflow-hidden shadow-sm">
                <div className="border-b p-4"><h2 className="font-semibold">Dernières prévisions à risque élevé</h2><p className="text-xs text-muted-foreground">Une notification et une recommandation peuvent être générées lorsque les actions sont activées.</p></div>
                {highRisk.length === 0 ? <div className="p-5"><EmptyState title="Aucun risque HIGH" description="Les seuils actuels ne détectent aucun équipement à risque élevé." icon={CheckCircle2} /></div> : <ForecastTable items={highRisk} equipmentMap={equipmentMap} canValidate={canValidate} onOpen={setCurrent} onValidate={openValidation} />}
              </Card>
            </TabsContent>

            <TabsContent value="batch">
              <Card className="p-5 shadow-sm">
                <div className="flex items-start gap-3"><div className="rounded-2xl bg-primary/10 p-3 text-primary"><Play className="h-5 w-5" /></div><div><h2 className="font-semibold">Analyse groupée du parc</h2><p className="text-xs text-muted-foreground">Le traitement analyse uniquement les équipements possédant un historique lié.</p></div></div>
                <div className="mt-5 grid gap-4 sm:grid-cols-3">
                  <Field label="Nombre d’équipements"><Input type="number" min="1" max="5000" value={batchLimit} onChange={(event) => setBatchLimit(event.target.value)} /></Field>
                  <Field label="Horizon"><Select value={horizon} onValueChange={setHorizon}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="30">30 jours</SelectItem><SelectItem value="90">90 jours</SelectItem><SelectItem value="180">180 jours</SelectItem><SelectItem value="365">365 jours</SelectItem></SelectContent></Select></Field>
                  <div className="flex items-end"><label className="flex h-10 items-center gap-2 rounded-xl border px-3 text-xs"><Checkbox checked={batchActions} onCheckedChange={(value) => setBatchActions(Boolean(value))} />Notifications et recommandations HIGH</label></div>
                </div>
                <Button className="mt-5" disabled={!canBatch || working} onClick={() => void runBatch()}>{working ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}Lancer le batch</Button>
                {!canBatch && <p className="mt-3 text-xs text-amber-700">Réservé aux rôles ADMIN et MANAGER.</p>}
              </Card>
            </TabsContent>

            <TabsContent value="runs">
              <Card className="overflow-hidden shadow-sm">
                <div className="border-b p-4"><h2 className="font-semibold">Historique des batches</h2><p className="text-xs text-muted-foreground">Traçabilité des exécutions automatiques et manuelles.</p></div>
                {runs.length === 0 ? <div className="p-5"><EmptyState title="Aucune exécution" description="Lancez un premier batch pour alimenter cet historique." icon={History} /></div> : (
                  <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Run</TableHead><TableHead>Date</TableHead><TableHead>Statut</TableHead><TableHead>Traités</TableHead><TableHead>HIGH</TableHead><TableHead>MEDIUM</TableHead><TableHead>LOW</TableHead><TableHead>Erreurs</TableHead></TableRow></TableHeader><TableBody>{runs.map((run) => <TableRow key={run.id}><TableCell className="font-semibold">#{run.id}</TableCell><TableCell>{formatDateTime(run.started_at)}</TableCell><TableCell><StatusBadge value={run.status} /></TableCell><TableCell>{run.processed_count}</TableCell><TableCell>{run.high_risk_count}</TableCell><TableCell>{run.medium_risk_count}</TableCell><TableCell>{run.low_risk_count}</TableCell><TableCell>{run.error_count}</TableCell></TableRow>)}</TableBody></Table></div>
                )}
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>

      <Dialog open={validationOpen} onOpenChange={setValidationOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Validation technique</DialogTitle><DialogDescription>Confirmez la cohérence de l’analyse. Le résultat réel de la panne peut rester inconnu jusqu’à la fin de l’horizon.</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <Field label="Décision"><Select value={validation.status} onValueChange={(value) => setValidation({ ...validation, status: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="CONFIRMED">Confirmée</SelectItem><SelectItem value="PARTIAL">Partiellement correcte</SelectItem><SelectItem value="REJECTED">Rejetée</SelectItem></SelectContent></Select></Field>
            <Field label="Notes"><Textarea value={validation.notes} onChange={(event) => setValidation({ ...validation, notes: event.target.value })} placeholder="Observations du technicien…" /></Field>
            <Field label="Panne réellement survenue"><Select value={validation.occurred} onValueChange={(value) => setValidation({ ...validation, occurred: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="UNKNOWN">Inconnu / horizon en cours</SelectItem><SelectItem value="YES">Oui</SelectItem><SelectItem value="NO">Non, horizon terminé</SelectItem></SelectContent></Select></Field>
            {validation.occurred === "YES" && <Field label="Date de la panne"><Input type="date" value={validation.date} onChange={(event) => setValidation({ ...validation, date: event.target.value })} /></Field>}
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setValidationOpen(false)}>Annuler</Button><Button onClick={() => void saveValidation()} disabled={working}>Enregistrer</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function ForecastCard({ item, equipment, canValidate, onValidate }: { item: FailureForecast; equipment?: Equipment; canValidate: boolean; onValidate: () => void }) {
  const percent = Math.round(item.failure_probability * 100)
  return (
    <Card className="overflow-hidden border-primary/15 shadow-sm">
      <div className="grid gap-5 p-5 lg:grid-cols-[250px_1fr]">
        <div className="rounded-3xl bg-gradient-to-br from-primary/10 to-emerald-50 p-5 dark:to-emerald-950/20">
          <div className="flex items-center justify-between"><StatusBadge value={item.risk_level} /><Badge variant="outline">{item.horizon_days} jours</Badge></div>
          <p className="mt-6 text-5xl font-black tracking-tight">{percent}%</p>
          <p className="mt-1 text-xs text-muted-foreground">Estimation heuristique non calibrée</p>
          <Progress value={percent} className="mt-4" />
          <div className="mt-5 space-y-2 text-xs"><p><span className="text-muted-foreground">Équipement :</span> <b>{equipment?.code ?? item.equipment_id}</b></p><p><span className="text-muted-foreground">Famille :</span> <b>{item.predicted_failure_family ?? "Non déterminée"}</b></p><p><span className="text-muted-foreground">Confiance :</span> <b>{item.evidence_confidence}</b></p><p><span className="text-muted-foreground">Moteur :</span> <b>{item.llm_used ? item.model_name : "Déterministe"}</b></p></div>
        </div>
        <div>
          <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-lg font-bold">Prévision #{item.id}</h2><p className="text-xs text-muted-foreground">Créée le {formatDateTime(item.forecasted_at)} · Fenêtre {formatDate(item.estimated_start_date)} → {formatDate(item.estimated_end_date)}</p></div><div className="flex gap-2"><StatusBadge value={item.validation_status} />{canValidate && <Button size="sm" variant="outline" onClick={onValidate}>Valider</Button>}</div></div>
          <p className="mt-4 whitespace-pre-line text-sm leading-relaxed text-muted-foreground">{item.explanation}</p>
          <div className="mt-5 grid gap-4 md:grid-cols-2"><ListBlock title="Facteurs calculés" items={item.factors} /><ListBlock title="Actions recommandées" items={item.recommended_actions} /></div>
          <div className="mt-4 flex flex-wrap gap-2">{item.similar_references.map((reference) => <Badge key={reference} variant="secondary">Cas {reference}</Badge>)}</div>
        </div>
      </div>
    </Card>
  )
}

function ForecastTable({ items, equipmentMap, canValidate, onOpen, onValidate }: { items: FailureForecast[]; equipmentMap: Map<number, Equipment>; canValidate: boolean; onOpen: (item: FailureForecast) => void; onValidate: (item: FailureForecast) => void }) {
  return <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Équipement</TableHead><TableHead>Score</TableHead><TableHead>Risque</TableHead><TableHead>Famille</TableHead><TableHead>Confiance</TableHead><TableHead>Validation</TableHead><TableHead>Date</TableHead><TableHead /></TableRow></TableHeader><TableBody>{items.map((item) => <TableRow key={item.id}><TableCell className="font-semibold">{equipmentMap.get(item.equipment_id)?.code ?? `#${item.equipment_id}`}</TableCell><TableCell>{item.risk_score}/100</TableCell><TableCell><StatusBadge value={item.risk_level} /></TableCell><TableCell>{item.predicted_failure_family ?? "—"}</TableCell><TableCell><StatusBadge value={item.evidence_confidence} /></TableCell><TableCell><StatusBadge value={item.validation_status} /></TableCell><TableCell>{formatDateTime(item.forecasted_at)}</TableCell><TableCell><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => onOpen(item)}>Voir</Button>{canValidate && <Button size="sm" onClick={() => onValidate(item)}>Valider</Button>}</div></TableCell></TableRow>)}</TableBody></Table></div>
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return <div className="rounded-2xl border bg-secondary/20 p-4"><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p><ul className="space-y-2 text-sm">{items.map((item, index) => <li key={`${item}-${index}`} className="flex gap-2"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />{item}</li>)}</ul></div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }

function Kpi({ label, value, icon: Icon, tone = "primary" }: { label: string; value: number; icon: typeof Gauge; tone?: "primary" | "red" | "amber" | "blue" | "green" }) {
  const colors = { primary: "bg-primary/10 text-primary", red: "bg-red-50 text-red-600 dark:bg-red-950/30", amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/30", blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/30", green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30" }
  return <Card className="p-4 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-3xl font-black">{value}</p></div><div className={`rounded-2xl p-3 ${colors[tone]}`}><Icon className="h-5 w-5" /></div></div></Card>
}
