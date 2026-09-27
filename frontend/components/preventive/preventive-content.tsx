"use client"

import { CalendarCheck2, CalendarClock, CheckCircle2, Play, Plus, Power, PowerOff, RefreshCcw, Stethoscope } from "lucide-react"
import { useEffect, useMemo, useState, type FormEvent } from "react"
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ApiError, apiFetch } from "@/lib/api"
import { formatDate, formatDateTime, formatMoney } from "@/lib/format"
import { hasRole, permissions } from "@/lib/permissions"
import type { Equipment, PreventiveExecution, PreventivePlan, User } from "@/lib/types"

const today = new Date().toISOString().slice(0, 10)

export function PreventiveContent() {
  const { user } = useAuth()
  const canManage = hasRole(user?.role, permissions.manager)
  const canExecute = hasRole(user?.role, permissions.technician)
  const [plans, setPlans] = useState<PreventivePlan[]>([])
  const [duePlans, setDuePlans] = useState<PreventivePlan[]>([])
  const [executions, setExecutions] = useState<PreventiveExecution[]>([])
  const [equipments, setEquipments] = useState<Equipment[]>([])
  const [technicians, setTechnicians] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [createOpen, setCreateOpen] = useState(false)
  const [executeOpen, setExecuteOpen] = useState(false)
  const [selected, setSelected] = useState<PreventivePlan | null>(null)
  const [working, setWorking] = useState(false)
  const [form, setForm] = useState({ equipment_id: "", title: "", description: "", frequency_days: "90", priority: "MEDIUM", assigned_technician_id: "", next_due_date: today })
  const [executionForm, setExecutionForm] = useState({ technician_id: "", estimated_cost: "0", notes: "" })

  const equipmentMap = useMemo(() => new Map(equipments.map((item) => [item.id, item])), [equipments])
  const technicianMap = useMemo(() => new Map(technicians.map((item) => [item.id, `${item.first_name} ${item.last_name}`])), [technicians])
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return plans.filter((plan) => {
      const equipment = equipmentMap.get(plan.equipment_id)
      return !query || [plan.title, equipment?.code, equipment?.brand, equipment?.model].filter(Boolean).some((value) => String(value).toLowerCase().includes(query))
    })
  }, [equipmentMap, plans, search])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const baseRequests = [
        apiFetch<PreventivePlan[]>("/preventive-maintenance/plans?limit=500"),
        apiFetch<PreventivePlan[]>("/preventive-maintenance/due?days_ahead=30&limit=500"),
        apiFetch<PreventiveExecution[]>("/preventive-maintenance/executions?limit=500"),
        apiFetch<Equipment[]>("/equipments?limit=200"),
      ] as const
      const [planData, dueData, executionData, equipmentData] = await Promise.all(baseRequests)
      setPlans(planData)
      setDuePlans(dueData)
      setExecutions(executionData)
      setEquipments(equipmentData)
      if (hasRole(user?.role, permissions.manager)) {
        try {
          const users = await apiFetch<User[]>("/users?limit=200")
          setTechnicians(users.filter((item) => item.role === "TECHNICIAN" && item.status === "ACTIVE"))
        } catch {
          setTechnicians([])
        }
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger la maintenance préventive.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [user?.role])

  async function createPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setWorking(true)
    try {
      const created = await apiFetch<PreventivePlan>("/preventive-maintenance/plans", {
        method: "POST",
        body: JSON.stringify({
          equipment_id: Number(form.equipment_id),
          title: form.title,
          description: form.description || null,
          frequency_days: Number(form.frequency_days),
          priority: form.priority,
          assigned_technician_id: form.assigned_technician_id ? Number(form.assigned_technician_id) : null,
          next_due_date: form.next_due_date,
        }),
      })
      setPlans((items) => [created, ...items])
      setCreateOpen(false)
      setForm({ equipment_id: "", title: "", description: "", frequency_days: "90", priority: "MEDIUM", assigned_technician_id: "", next_due_date: today })
      toast.success("Plan préventif créé")
      await loadData()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Création impossible.")
    } finally {
      setWorking(false)
    }
  }

  async function togglePlan(plan: PreventivePlan) {
    setWorking(true)
    try {
      const endpoint = plan.active ? "deactivate" : "activate"
      const updated = await apiFetch<PreventivePlan>(`/preventive-maintenance/plans/${plan.id}/${endpoint}`, { method: "POST" })
      setPlans((items) => items.map((item) => item.id === updated.id ? updated : item))
      toast.success(plan.active ? "Plan désactivé" : "Plan activé")
      await loadData()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Opération impossible.")
    } finally {
      setWorking(false)
    }
  }

  function openExecute(plan: PreventivePlan) {
    setSelected(plan)
    setExecutionForm({ technician_id: plan.assigned_technician_id ? String(plan.assigned_technician_id) : "", estimated_cost: "0", notes: "" })
    setExecuteOpen(true)
  }

  async function executePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected) return
    setWorking(true)
    try {
      await apiFetch<PreventiveExecution>(`/preventive-maintenance/plans/${selected.id}/execute`, {
        method: "POST",
        body: JSON.stringify({
          technician_id: executionForm.technician_id ? Number(executionForm.technician_id) : null,
          estimated_cost: Number(executionForm.estimated_cost || 0),
          notes: executionForm.notes || null,
        }),
      })
      setExecuteOpen(false)
      toast.success("Intervention préventive générée")
      await loadData()
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Exécution impossible.")
    } finally {
      setWorking(false)
    }
  }

  const overdue = plans.filter((item) => item.active && item.next_due_date < today).length

  return (
    <>
      <Header
        title="Maintenance préventive"
        description="Planifiez les contrôles récurrents, suivez les échéances et générez automatiquement les interventions."
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Plan, code équipement, marque ou modèle"
        actions={<>{canManage && <Dialog open={createOpen} onOpenChange={setCreateOpen}><DialogTrigger asChild><Button className="h-9"><Plus className="mr-2 h-4 w-4" />Nouveau plan</Button></DialogTrigger><DialogContent className="sm:max-w-2xl"><form onSubmit={createPlan}><DialogHeader><DialogTitle>Nouveau plan préventif</DialogTitle><DialogDescription>Définissez une périodicité et une prochaine échéance.</DialogDescription></DialogHeader><div className="mt-5 grid gap-4 sm:grid-cols-2"><Field label="Équipement *"><Select value={form.equipment_id} onValueChange={(value) => setForm({ ...form, equipment_id: value })}><SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{equipments.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.code} · {[item.brand, item.model].filter(Boolean).join(" ")}</SelectItem>)}</SelectContent></Select></Field><Field label="Titre *"><Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required minLength={3} /></Field><div className="sm:col-span-2"><Field label="Description"><Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field></div><Field label="Fréquence (jours) *"><Input type="number" min="1" max="3650" value={form.frequency_days} onChange={(event) => setForm({ ...form, frequency_days: event.target.value })} required /></Field><Field label="Prochaine échéance *"><Input type="date" value={form.next_due_date} onChange={(event) => setForm({ ...form, next_due_date: event.target.value })} required /></Field><Field label="Priorité"><Select value={form.priority} onValueChange={(value) => setForm({ ...form, priority: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="LOW">Faible</SelectItem><SelectItem value="MEDIUM">Moyenne</SelectItem><SelectItem value="HIGH">Élevée</SelectItem><SelectItem value="CRITICAL">Critique</SelectItem></SelectContent></Select></Field><Field label="Technicien"><Select value={form.assigned_technician_id || "NONE"} onValueChange={(value) => setForm({ ...form, assigned_technician_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue placeholder="Non affecté" /></SelectTrigger><SelectContent><SelectItem value="NONE">Non affecté</SelectItem>{technicians.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.first_name} {item.last_name}</SelectItem>)}</SelectContent></Select></Field></div><DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Annuler</Button><Button type="submit" disabled={working || !form.equipment_id}>{working ? "Création…" : "Créer"}</Button></DialogFooter></form></DialogContent></Dialog>}<Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button></>}
      />

      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi label="Plans actifs" value={plans.filter((item) => item.active).length} icon={CalendarCheck2} />
          <Kpi label="Échéances à 30 jours" value={duePlans.length} icon={CalendarClock} tone="amber" />
          <Kpi label="Plans en retard" value={overdue} icon={Stethoscope} tone="red" />
          <Kpi label="Exécutions" value={executions.length} icon={CheckCircle2} tone="green" />
        </div>

        {loading ? <LoadingState /> : (
          <Tabs defaultValue="plans" className="space-y-4">
            <TabsList><TabsTrigger value="plans">Plans</TabsTrigger><TabsTrigger value="due">Échéances</TabsTrigger><TabsTrigger value="executions">Exécutions</TabsTrigger></TabsList>
            <TabsContent value="plans"><PlanTable plans={filtered} equipmentMap={equipmentMap} technicianMap={technicianMap} canManage={canManage} canExecute={canExecute} onToggle={togglePlan} onExecute={openExecute} /></TabsContent>
            <TabsContent value="due"><PlanTable plans={duePlans} equipmentMap={equipmentMap} technicianMap={technicianMap} canManage={canManage} canExecute={canExecute} onToggle={togglePlan} onExecute={openExecute} /></TabsContent>
            <TabsContent value="executions"><Card className="overflow-hidden shadow-sm">{executions.length === 0 ? <div className="p-5"><EmptyState title="Aucune exécution" description="Exécutez un plan préventif pour créer automatiquement une intervention." icon={Play} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Exécution</TableHead><TableHead>Plan</TableHead><TableHead>Intervention</TableHead><TableHead>Date prévue</TableHead><TableHead>Déclenchement</TableHead><TableHead>Statut</TableHead><TableHead>Notes</TableHead></TableRow></TableHeader><TableBody>{executions.map((item) => <TableRow key={item.id}><TableCell className="font-semibold">#{item.id}</TableCell><TableCell>Plan #{item.plan_id}</TableCell><TableCell>INT #{item.intervention_id}</TableCell><TableCell>{formatDate(item.scheduled_date)}</TableCell><TableCell>{formatDateTime(item.triggered_at)}</TableCell><TableCell><StatusBadge value={item.status} /></TableCell><TableCell className="max-w-72"><p className="line-clamp-2">{item.notes || "—"}</p></TableCell></TableRow>)}</TableBody></Table></div>}</Card></TabsContent>
          </Tabs>
        )}
      </div>

      <Dialog open={executeOpen} onOpenChange={setExecuteOpen}>
        <DialogContent>
          <form onSubmit={executePlan}>
            <DialogHeader><DialogTitle>Exécuter le plan</DialogTitle><DialogDescription>Une intervention PREVENTIVE sera créée et l’équipement passera en maintenance.</DialogDescription></DialogHeader>
            <div className="mt-5 space-y-4"><Field label="Technicien"><Select value={executionForm.technician_id || "NONE"} onValueChange={(value) => setExecutionForm({ ...executionForm, technician_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="NONE">Technicien du plan</SelectItem>{technicians.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.first_name} {item.last_name}</SelectItem>)}</SelectContent></Select></Field><Field label="Coût estimé (MAD)"><Input type="number" min="0" step="0.01" value={executionForm.estimated_cost} onChange={(event) => setExecutionForm({ ...executionForm, estimated_cost: event.target.value })} /></Field><Field label="Notes"><Textarea value={executionForm.notes} onChange={(event) => setExecutionForm({ ...executionForm, notes: event.target.value })} /></Field></div>
            <DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setExecuteOpen(false)}>Annuler</Button><Button type="submit" disabled={working}>{working ? "Exécution…" : "Créer l’intervention"}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

function PlanTable({ plans, equipmentMap, technicianMap, canManage, canExecute, onToggle, onExecute }: { plans: PreventivePlan[]; equipmentMap: Map<number, Equipment>; technicianMap: Map<number, string>; canManage: boolean; canExecute: boolean; onToggle: (plan: PreventivePlan) => void; onExecute: (plan: PreventivePlan) => void }) {
  if (plans.length === 0) return <Card className="p-5"><EmptyState title="Aucun plan" description="Créez le premier plan de maintenance préventive." icon={CalendarCheck2} /></Card>
  return <Card className="overflow-hidden shadow-sm"><div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Plan</TableHead><TableHead>Équipement</TableHead><TableHead>Fréquence</TableHead><TableHead>Échéance</TableHead><TableHead>Priorité</TableHead><TableHead>Technicien</TableHead><TableHead>État</TableHead><TableHead /></TableRow></TableHeader><TableBody>{plans.map((plan) => { const equipment = equipmentMap.get(plan.equipment_id); const overdue = plan.active && plan.next_due_date < today; return <TableRow key={plan.id}><TableCell><p className="font-semibold">{plan.title}</p><p className="max-w-72 truncate text-xs text-muted-foreground">{plan.description || "—"}</p></TableCell><TableCell><p className="font-medium">{equipment?.code ?? `#${plan.equipment_id}`}</p><p className="text-xs text-muted-foreground">{[equipment?.brand, equipment?.model].filter(Boolean).join(" ")}</p></TableCell><TableCell>Tous les {plan.frequency_days} jours</TableCell><TableCell><p className={overdue ? "font-semibold text-red-600" : ""}>{formatDate(plan.next_due_date)}</p>{overdue && <p className="text-[10px] text-red-600">En retard</p>}</TableCell><TableCell><StatusBadge value={plan.priority} /></TableCell><TableCell>{plan.assigned_technician_id ? technicianMap.get(plan.assigned_technician_id) ?? `#${plan.assigned_technician_id}` : "Non affecté"}</TableCell><TableCell><StatusBadge value={plan.active ? "ACTIVE" : "INACTIVE"} /></TableCell><TableCell><div className="flex gap-2">{canExecute && plan.active && <Button size="sm" onClick={() => onExecute(plan)}><Play className="mr-1 h-3.5 w-3.5" />Exécuter</Button>}{canManage && <Button size="sm" variant="outline" onClick={() => void onToggle(plan)}>{plan.active ? <PowerOff className="h-3.5 w-3.5" /> : <Power className="h-3.5 w-3.5" />}</Button>}</div></TableCell></TableRow> })}</TableBody></Table></div></Card>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }
function Kpi({ label, value, icon: Icon, tone = "primary" }: { label: string; value: number; icon: typeof CalendarCheck2; tone?: "primary" | "amber" | "red" | "green" }) { const colors = { primary: "bg-primary/10 text-primary", amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/30", red: "bg-red-50 text-red-600 dark:bg-red-950/30", green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30" }; return <Card className="p-4 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-3xl font-black">{value}</p></div><div className={`rounded-2xl p-3 ${colors[tone]}`}><Icon className="h-5 w-5" /></div></div></Card> }
