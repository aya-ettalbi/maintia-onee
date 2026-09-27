"use client"

import { CalendarClock, CheckCircle2, Gauge, Plus, RefreshCcw, Sparkles } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { useAuth } from "@/components/auth/auth-provider"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { StatusBadge } from "@/components/common/status-badge"
import { Header } from "@/components/dashboard/header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { apiFetch, ApiError } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { statusLabel } from "@/lib/status"
import type { Equipment, Recommendation } from "@/lib/types"

const statuses = ["NEW", "TO_REVIEW", "ACCEPTED", "PLANNED", "IN_PROGRESS", "APPLIED", "REJECTED", "EXPIRED"]

export function RecommendationsContent() {
  const { user } = useAuth()
  const canManage = ["ADMIN", "MANAGER"].includes(user?.role ?? "")
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [equipments, setEquipments] = useState<Equipment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState("ALL")
  const [generateOpen, setGenerateOpen] = useState(false)
  const [selectedEquipment, setSelectedEquipment] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [recommendationData, equipmentData] = await Promise.all([
        apiFetch<Recommendation[]>("/recommendations?limit=200"),
        apiFetch<Equipment[]>("/equipments?limit=200"),
      ])
      setRecommendations(recommendationData)
      setEquipments(equipmentData)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les recommandations.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [])

  const equipmentMap = useMemo(() => new Map(equipments.map((item) => [item.id, item])), [equipments])
  const filtered = useMemo(() => recommendations.filter((item) => statusFilter === "ALL" || item.status === statusFilter), [recommendations, statusFilter])

  async function generate() {
    if (!selectedEquipment) return
    setSubmitting(true)
    try {
      const created = await apiFetch<Recommendation>(`/recommendations/generate/equipment/${selectedEquipment}`, { method: "POST" })
      setRecommendations((current) => [created, ...current])
      setGenerateOpen(false)
      setSelectedEquipment("")
      toast.success("Recommandation intelligente générée")
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Génération impossible.")
    } finally {
      setSubmitting(false)
    }
  }

  async function updateStatus(item: Recommendation, status: string) {
    try {
      const updated = await apiFetch<Recommendation>(`/recommendations/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status, due_date: item.due_date }),
      })
      setRecommendations((current) => current.map((recommendation) => recommendation.id === updated.id ? updated : recommendation))
      toast.success("Statut de la recommandation mis à jour")
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Mise à jour impossible.")
    }
  }

  return (
    <>
      <Header
        title="Recommandations intelligentes"
        description="Transformez les indicateurs de risque en actions préventives, décisions de renouvellement et priorités opérationnelles."
        actions={
          <>
            {canManage && (
              <Dialog open={generateOpen} onOpenChange={setGenerateOpen}>
                <DialogTrigger asChild><Button className="h-9 shadow-lg shadow-primary/20"><Plus className="mr-2 h-4 w-4" />Générer une recommandation</Button></DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>Nouvelle recommandation</DialogTitle><DialogDescription>Le backend calculera le score de risque et produira une action justifiée.</DialogDescription></DialogHeader>
                  <div className="mt-5 space-y-2"><Label>Équipement</Label><Select value={selectedEquipment} onValueChange={setSelectedEquipment}><SelectTrigger className="w-full"><SelectValue placeholder="Sélectionner un équipement" /></SelectTrigger><SelectContent>{equipments.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.code} · {[item.brand, item.model].filter(Boolean).join(" ")}</SelectItem>)}</SelectContent></Select></div>
                  <DialogFooter className="mt-6"><Button variant="outline" onClick={() => setGenerateOpen(false)}>Annuler</Button><Button onClick={() => void generate()} disabled={!selectedEquipment || submitting}>{submitting ? "Génération…" : "Générer"}</Button></DialogFooter>
                </DialogContent>
              </Dialog>
            )}
            <Button variant="outline" className="h-9 bg-transparent" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button>
          </>
        }
      />

      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}

        <div className="grid gap-3 sm:grid-cols-4">
          <Summary label="Recommandations" value={recommendations.length} icon={Sparkles} />
          <Summary label="Risque élevé" value={recommendations.filter((item) => item.risk_level === "HIGH").length} icon={Gauge} tone="red" />
          <Summary label="À traiter" value={recommendations.filter((item) => ["NEW", "TO_REVIEW", "ACCEPTED", "PLANNED", "IN_PROGRESS"].includes(item.status)).length} icon={CalendarClock} tone="amber" />
          <Summary label="Appliquées" value={recommendations.filter((item) => item.status === "APPLIED").length} icon={CheckCircle2} tone="green" />
        </div>

        <div className="flex justify-end"><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-52"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">Tous les statuts</SelectItem>{statuses.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></div>

        {loading ? <LoadingState /> : filtered.length === 0 ? <EmptyState title="Aucune recommandation" description="Générez une recommandation à partir du score de risque d’un équipement." icon={Sparkles} /> : (
          <div className="grid gap-4 lg:grid-cols-2">
            {filtered.map((item) => {
              const equipment = item.equipment_id ? equipmentMap.get(item.equipment_id) : undefined
              return (
                <Card key={item.id} className="overflow-hidden border-border/80 bg-card shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl">
                  <div className="border-b border-border/70 p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0"><div className="mb-2 flex flex-wrap items-center gap-2"><StatusBadge value={item.priority} /><StatusBadge value={item.status} /></div><h2 className="font-semibold">{item.title}</h2><p className="mt-1 text-xs text-muted-foreground">{equipment ? `${equipment.code} · ${[equipment.brand, equipment.model].filter(Boolean).join(" ")}` : "Recommandation générale"}</p></div>
                      <div className="text-right"><p className="text-3xl font-bold text-primary">{Math.round(item.risk_score)}</p><p className="text-[10px] uppercase tracking-wider text-muted-foreground">score / 100</p></div>
                    </div>
                    <Progress value={item.risk_score} className="mt-4 h-2" />
                  </div>

                  <div className="space-y-4 p-5">
                    <div><p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Observation</p><p className="mt-1 text-sm leading-relaxed">{item.observation}</p></div>
                    <div><p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Justification</p><p className="mt-1 text-sm leading-relaxed text-muted-foreground">{item.justification || "Aucune justification détaillée."}</p></div>
                    <div className="rounded-xl bg-primary/10 p-4"><p className="text-xs font-semibold text-primary">Action recommandée</p><p className="mt-1 text-sm leading-relaxed">{item.recommended_action}</p></div>
                    <div className="flex flex-col gap-3 border-t border-border/70 pt-4 sm:flex-row sm:items-end sm:justify-between">
                      <div><p className="text-[10px] uppercase tracking-wider text-muted-foreground">Échéance</p><p className="mt-1 text-sm font-medium">{formatDate(item.due_date)}</p></div>
                      {canManage && <div className="space-y-1.5"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">Mettre à jour</p><Select value={item.status} onValueChange={(value) => void updateStatus(item, value)}><SelectTrigger className="w-48"><SelectValue /></SelectTrigger><SelectContent>{statuses.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></div>}
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}

function Summary({ label, value, icon: Icon, tone = "primary" }: { label: string; value: number; icon: typeof Sparkles; tone?: "primary" | "red" | "amber" | "green" }) {
  const color = tone === "red" ? "bg-red-50 text-red-600 dark:bg-red-950/30" : tone === "amber" ? "bg-amber-50 text-amber-600 dark:bg-amber-950/30" : tone === "green" ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30" : "bg-primary/10 text-primary"
  return <div className="flex items-center justify-between rounded-2xl border bg-card p-4 shadow-sm"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-3xl font-bold">{value}</p></div><div className={`rounded-xl p-3 ${color}`}><Icon className="h-5 w-5" /></div></div>
}
