"use client"

import { AlertTriangle, Bot, BrainCircuit, Boxes, Gauge, LoaderCircle, MessageSquareText, RefreshCcw, Search, Send, Sparkles, Wrench } from "lucide-react"
import { useEffect, useMemo, useState, type FormEvent } from "react"
import { toast } from "sonner"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { StatusBadge } from "@/components/common/status-badge"
import { Header } from "@/components/dashboard/header"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ApiError, apiFetch } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import type { ChatResponse, DiagnosticSuggestion, Equipment, RecurrentFailuresResponse, RiskAssessment, StockShortageRisksResponse, TriageResponse } from "@/lib/types"

export function AiContent() {
  const [equipments, setEquipments] = useState<Equipment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [working, setWorking] = useState(false)

  const [chatMessage, setChatMessage] = useState("")
  const [chat, setChat] = useState<ChatResponse | null>(null)
  const [triageDescription, setTriageDescription] = useState("")
  const [triageCode, setTriageCode] = useState("")
  const [triage, setTriage] = useState<TriageResponse | null>(null)
  const [diagnosticDescription, setDiagnosticDescription] = useState("")
  const [diagnostics, setDiagnostics] = useState<DiagnosticSuggestion[]>([])
  const [selectedEquipment, setSelectedEquipment] = useState("")
  const [risk, setRisk] = useState<RiskAssessment | null>(null)
  const [recurrent, setRecurrent] = useState<RecurrentFailuresResponse | null>(null)
  const [stockRisks, setStockRisks] = useState<StockShortageRisksResponse | null>(null)

  const equipmentMap = useMemo(() => new Map(equipments.map((item) => [item.id, item])), [equipments])

  async function loadBase() {
    setLoading(true)
    setError(null)
    try {
      setEquipments(await apiFetch<Equipment[]>("/equipments?limit=200"))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger le module IA.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadBase() }, [])

  async function askChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (chatMessage.trim().length < 5) return
    setWorking(true)
    try {
      const response = await apiFetch<ChatResponse>("/chat", {
        method: "POST",
        timeoutMs: 120_000,
        body: JSON.stringify({ message: chatMessage.trim(), candidate_k: 30, top_k: 6 }),
      })
      setChat(response)
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Assistant indisponible.")
    } finally {
      setWorking(false)
    }
  }

  async function runTriage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setWorking(true)
    try {
      setTriage(await apiFetch<TriageResponse>("/ai/triage", { method: "POST", body: JSON.stringify({ description: triageDescription, equipment_code: triageCode || null }) }))
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Triage impossible.")
    } finally { setWorking(false) }
  }

  async function runDiagnostic(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setWorking(true)
    try {
      setDiagnostics(await apiFetch<DiagnosticSuggestion[]>("/historical/diagnostic-suggestions", { method: "POST", body: JSON.stringify({ description: diagnosticDescription, top_k: 8 }) }))
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Recherche impossible.")
    } finally { setWorking(false) }
  }

  async function loadRisk() {
    if (!selectedEquipment) return
    setWorking(true)
    try {
      setRisk(await apiFetch<RiskAssessment>(`/ai/equipments/${selectedEquipment}/risk-assessment`))
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Calcul impossible.")
    } finally { setWorking(false) }
  }

  async function loadAnalytics() {
    setWorking(true)
    try {
      const [failureData, stockData] = await Promise.all([
        apiFetch<RecurrentFailuresResponse>("/ai/analytics/recurrent-failures?period_months=24&minimum_occurrences=3&limit=50"),
        apiFetch<StockShortageRisksResponse>("/ai/stock/shortage-risks?lookback_days=90&limit=100"),
      ])
      setRecurrent(failureData)
      setStockRisks(stockData)
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Analyse impossible.")
    } finally { setWorking(false) }
  }

  return (
    <>
      <Header title="Assistant MaintIA" description="Chatbot RAG, triage, diagnostic historique, risque équipement et analyses prédictives." actions={<Button variant="outline" className="h-9 bg-card" onClick={() => void loadBase()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button>} />
      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        <Alert className="border-primary/20 bg-primary/[0.035]"><BrainCircuit className="h-4 w-4" /><AlertDescription>Les chiffres viennent de PostgreSQL et des règles déterministes. OpenRouter explique les preuves sans inventer de panne, de date ou de coût.</AlertDescription></Alert>
        {loading ? <LoadingState /> : (
          <Tabs defaultValue="chat" className="space-y-4">
            <TabsList className="grid h-auto w-full grid-cols-2 gap-1 md:w-auto md:grid-cols-5"><TabsTrigger value="chat">Chat RAG</TabsTrigger><TabsTrigger value="triage">Triage</TabsTrigger><TabsTrigger value="diagnostic">Diagnostic</TabsTrigger><TabsTrigger value="risk">Risque</TabsTrigger><TabsTrigger value="analytics" onClick={() => !recurrent && void loadAnalytics()}>Analyses</TabsTrigger></TabsList>

            <TabsContent value="chat" className="space-y-4">
              <Card className="overflow-hidden shadow-sm">
                <div className="border-b bg-primary/[0.035] p-4"><div className="flex items-center gap-3"><div className="rounded-2xl bg-primary/10 p-3 text-primary"><Bot className="h-5 w-5" /></div><div><h2 className="font-semibold">Copilote de maintenance</h2><p className="text-xs text-muted-foreground">Décrivez un symptôme ou demandez l’historique d’un équipement.</p></div></div></div>
                <form onSubmit={askChat} className="p-4"><div className="flex gap-2"><Textarea className="min-h-24 flex-1" value={chatMessage} onChange={(event) => setChatMessage(event.target.value)} placeholder="Ex. L’imprimante fait un bruit inhabituel et le papier reste bloqué…" /><Button type="submit" disabled={working || chatMessage.trim().length < 5} className="h-auto px-5">{working ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}</Button></div></form>
              </Card>
              {chat ? <Card className="overflow-hidden shadow-sm"><div className="border-b p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-semibold">Réponse MaintIA</h2><p className="text-xs text-muted-foreground">Intent {chat.intent} · {chat.classification_group ?? "sans groupe"}</p></div><div className="flex gap-2"><StatusBadge value={chat.confidence} /><Badge variant="outline">Confiance {chat.confidence_score}%</Badge><Badge variant="secondary">{chat.llm_used ? chat.model : "Fallback déterministe"}</Badge></div></div></div><div className="space-y-5 p-5"><p className="whitespace-pre-line text-sm leading-7">{chat.summary}</p><div className="grid gap-4 md:grid-cols-3"><AiList title="Causes probables" items={chat.probable_causes} /><AiList title="Vérifications" items={chat.recommended_checks} /><AiList title="Solutions historiques" items={chat.historical_solutions} /></div>{chat.warnings.length > 0 && <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/20 dark:text-amber-100">{chat.warnings.map((item) => <p key={item}>• {item}</p>)}</div>}<div><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sources RAG</p><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{chat.sources.map((source, index) => <div key={`${source.reference}-${index}`} className="rounded-xl border p-3 text-xs"><div className="flex justify-between"><b>{source.reference ?? "Cas historique"}</b><span>{Math.round(source.final_score * 100)}%</span></div><p className="mt-1 text-muted-foreground">{source.classification ?? "Classification non renseignée"}</p><p className="mt-1">Lien équipement : {source.link_trust ?? "—"}</p></div>)}</div></div></div></Card> : <EmptyState title="Posez une question à MaintIA" description="La réponse s’appuiera sur les demandes historiques vectorisées dans Qdrant." icon={MessageSquareText} />}
            </TabsContent>

            <TabsContent value="triage"><div className="grid gap-4 lg:grid-cols-2"><Card className="p-5 shadow-sm"><form onSubmit={runTriage} className="space-y-4"><div><h2 className="font-semibold">Classification automatique</h2><p className="text-xs text-muted-foreground">Détermine le type d’incident, la priorité et l’équipe suggérée.</p></div><Field label="Description"><Textarea minLength={5} required value={triageDescription} onChange={(event) => setTriageDescription(event.target.value)} /></Field><Field label="Code équipement (facultatif)"><Input value={triageCode} onChange={(event) => setTriageCode(event.target.value)} placeholder="UC110570" /></Field><Button type="submit" disabled={working}><Sparkles className="mr-2 h-4 w-4" />Analyser</Button></form></Card>{triage ? <Card className="p-5 shadow-sm"><div className="flex items-center justify-between"><h2 className="font-semibold">Résultat du triage</h2><StatusBadge value={triage.confidence} /></div><div className="mt-5 grid grid-cols-2 gap-3"><Metric label="Type" value={triage.incident_type} /><Metric label="Groupe" value={triage.classification_group} /><Metric label="Priorité" value={triage.suggested_priority} /><Metric label="Équipe" value={triage.suggested_team} /></div><p className="mt-4 text-xs text-muted-foreground">Règles : {triage.matched_rules.join(" · ") || "Aucune règle explicite"}</p><Progress className="mt-4" value={triage.confidence_score} /></Card> : <EmptyState title="Aucun triage" description="Saisissez la description d’une nouvelle demande." icon={Sparkles} />}</div></TabsContent>

            <TabsContent value="diagnostic"><div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]"><Card className="p-5 shadow-sm"><form onSubmit={runDiagnostic} className="space-y-4"><div><h2 className="font-semibold">Cas similaires</h2><p className="text-xs text-muted-foreground">Recherche les diagnostics et solutions observés dans l’historique.</p></div><Field label="Symptôme"><Textarea minLength={5} required value={diagnosticDescription} onChange={(event) => setDiagnosticDescription(event.target.value)} /></Field><Button type="submit" disabled={working}><Search className="mr-2 h-4 w-4" />Rechercher</Button></form></Card><Card className="overflow-hidden shadow-sm">{diagnostics.length === 0 ? <div className="p-5"><EmptyState title="Aucun résultat" description="Décrivez précisément le symptôme observé." icon={Wrench} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Similarité</TableHead><TableHead>Diagnostic</TableHead><TableHead>Solution</TableHead></TableRow></TableHeader><TableBody>{diagnostics.map((item) => <TableRow key={item.intervention_id}><TableCell><Badge>{Math.round(item.similarity * 100)}%</Badge></TableCell><TableCell className="max-w-sm">{item.diagnosis || "—"}</TableCell><TableCell className="max-w-lg">{item.solution || "—"}</TableCell></TableRow>)}</TableBody></Table></div>}</Card></div></TabsContent>

            <TabsContent value="risk"><div className="grid gap-4 lg:grid-cols-[0.7fr_1.3fr]"><Card className="p-5 shadow-sm"><h2 className="font-semibold">Évaluation avancée</h2><p className="mb-4 text-xs text-muted-foreground">Score basé sur l’âge, l’état et les incidents disponibles.</p><Field label="Équipement"><Select value={selectedEquipment} onValueChange={setSelectedEquipment}><SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{equipments.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.code} · {[item.brand, item.model].filter(Boolean).join(" ")}</SelectItem>)}</SelectContent></Select></Field><Button className="mt-4" onClick={() => void loadRisk()} disabled={!selectedEquipment || working}><Gauge className="mr-2 h-4 w-4" />Calculer le risque</Button></Card>{risk ? <Card className="p-5 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="font-semibold">{risk.equipment_code}</h2><p className="text-xs text-muted-foreground">Version {risk.calculation_version} · {formatDateTime(risk.calculated_at)}</p></div><StatusBadge value={risk.level} /></div><p className="mt-5 text-5xl font-black">{risk.score}<span className="text-xl text-muted-foreground">/100</span></p><Progress className="mt-3" value={risk.score} /><AiList title="Facteurs" items={risk.factors} /><div className="mt-4 rounded-xl bg-primary/5 p-4 text-sm">{risk.recommended_action}</div></Card> : <EmptyState title="Aucun score" description="Choisissez un équipement pour calculer son risque." icon={Gauge} />}</div></TabsContent>

            <TabsContent value="analytics" className="space-y-4"><div className="flex justify-end"><Button variant="outline" onClick={() => void loadAnalytics()} disabled={working}><RefreshCcw className="mr-2 h-4 w-4" />Recalculer</Button></div><div className="grid gap-4 xl:grid-cols-2"><Card className="overflow-hidden shadow-sm"><div className="border-b p-4"><h2 className="font-semibold">Pannes récurrentes</h2><p className="text-xs text-muted-foreground">Groupes les plus fréquents sur 24 mois.</p></div>{!recurrent ? <div className="p-5"><LoadingState /></div> : recurrent.items.length === 0 ? <div className="p-5"><EmptyState title="Aucune récurrence" description="Aucun groupe ne dépasse le seuil." icon={AlertTriangle} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Classification</TableHead><TableHead>Occurrences</TableHead><TableHead>Dernière date</TableHead></TableRow></TableHeader><TableBody>{recurrent.items.map((item) => <TableRow key={item.classification}><TableCell className="font-medium">{item.classification}</TableCell><TableCell>{item.occurrence_count}</TableCell><TableCell>{formatDateTime(item.latest_date)}</TableCell></TableRow>)}</TableBody></Table></div>}</Card><Card className="overflow-hidden shadow-sm"><div className="border-b p-4"><h2 className="font-semibold">Risque de rupture de stock</h2><p className="text-xs text-muted-foreground">Projection à partir des sorties récentes.</p></div>{!stockRisks ? <div className="p-5"><LoadingState /></div> : stockRisks.items.length === 0 ? <div className="p-5"><EmptyState title="Aucun risque" description="Les consommations disponibles ne signalent pas de rupture." icon={Boxes} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Pièce</TableHead><TableHead>Stock</TableHead><TableHead>Couverture</TableHead><TableHead>Commande</TableHead><TableHead>Risque</TableHead></TableRow></TableHeader><TableBody>{stockRisks.items.map((item) => <TableRow key={item.part_id}><TableCell><p className="font-medium">{item.part_code}</p><p className="text-xs text-muted-foreground">{item.part_name}</p></TableCell><TableCell>{item.current_quantity}</TableCell><TableCell>{item.months_of_coverage === null ? "—" : `${item.months_of_coverage.toFixed(1)} mois`}</TableCell><TableCell>{item.suggested_order_quantity}</TableCell><TableCell><StatusBadge value={item.risk} /></TableCell></TableRow>)}</TableBody></Table></div>}</Card></div></TabsContent>
          </Tabs>
        )}
      </div>
    </>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }
function AiList({ title, items }: { title: string; items: string[] }) { return <div className="mt-4 rounded-2xl border bg-secondary/20 p-4"><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p>{items.length === 0 ? <p className="text-xs text-muted-foreground">Aucune donnée.</p> : <ul className="space-y-2 text-sm">{items.map((item, index) => <li key={`${item}-${index}`} className="flex gap-2"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />{item}</li>)}</ul>}</div> }
function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border bg-secondary/20 p-3"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></div> }
