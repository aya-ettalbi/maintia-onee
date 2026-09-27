"use client"

import { Ban, ClipboardCheck, ClipboardList, Pencil, Plus, RefreshCcw, UserCheck } from "lucide-react"
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
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { ApiError, apiFetch } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { hasRole, permissions } from "@/lib/permissions"
import { statusLabel } from "@/lib/status"
import type { Equipment, MaintenanceRequest, User } from "@/lib/types"

const statuses = ["DRAFT", "SUBMITTED", "VALIDATED", "REJECTED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED", "CANCELLED"]

export function RequestsContent() {
  const { user } = useAuth()
  const canManage = hasRole(user?.role, permissions.manager)
  const [items, setItems] = useState<MaintenanceRequest[]>([])
  const [equipments, setEquipments] = useState<Equipment[]>([])
  const [technicians, setTechnicians] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("ALL")
  const [dialog, setDialog] = useState<"create" | "edit" | null>(null)
  const [selected, setSelected] = useState<MaintenanceRequest | null>(null)
  const [working, setWorking] = useState(false)
  const [form, setForm] = useState({ equipment_id: "", description: "", category: "", priority: "MEDIUM", status: "SUBMITTED", assigned_technician_id: "" })

  const equipmentMap = useMemo(() => new Map(equipments.map((item) => [item.id, item])), [equipments])
  const technicianMap = useMemo(() => new Map(technicians.map((item) => [item.id, `${item.first_name} ${item.last_name}`])), [technicians])
  const filtered = useMemo(() => { const query = search.trim().toLowerCase(); return items.filter((item) => { const equipment = equipmentMap.get(item.equipment_id); const matches = !query || [item.reference, item.description, item.category, equipment?.code].filter(Boolean).some((value) => String(value).toLowerCase().includes(query)); return matches && (statusFilter === "ALL" || item.status === statusFilter) }) }, [equipmentMap, items, search, statusFilter])

  async function loadData() {
    setLoading(true); setError(null)
    try {
      const [requestData, equipmentData] = await Promise.all([apiFetch<MaintenanceRequest[]>("/maintenance-requests?limit=200"), apiFetch<Equipment[]>("/equipments?limit=200")])
      setItems(requestData); setEquipments(equipmentData)
      if (canManage) { try { const users = await apiFetch<User[]>("/users?limit=200"); setTechnicians(users.filter((item) => item.role === "TECHNICIAN" && item.status === "ACTIVE")) } catch { setTechnicians([]) } }
    } catch (caught) { setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les demandes.") } finally { setLoading(false) }
  }
  useEffect(() => { void loadData() }, [canManage])

  function openCreate() { setSelected(null); setForm({ equipment_id: "", description: "", category: "", priority: "MEDIUM", status: "SUBMITTED", assigned_technician_id: "" }); setDialog("create") }
  function openEdit(item: MaintenanceRequest) { setSelected(item); setForm({ equipment_id: String(item.equipment_id), description: item.description, category: item.category ?? "", priority: item.priority, status: item.status, assigned_technician_id: item.assigned_technician_id ? String(item.assigned_technician_id) : "" }); setDialog("edit") }

  async function saveRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setWorking(true)
    try {
      if (dialog === "create") {
        const created = await apiFetch<MaintenanceRequest>("/maintenance-requests", { method: "POST", body: JSON.stringify({ equipment_id: Number(form.equipment_id), description: form.description, category: form.category || null, priority: form.priority }) })
        setItems((current) => [created, ...current]); toast.success("Demande créée")
      } else if (selected) {
        let updated = await apiFetch<MaintenanceRequest>(`/maintenance-requests/${selected.id}`, { method: "PATCH", body: JSON.stringify({ description: form.description, category: form.category || null, priority: form.priority, assigned_technician_id: form.assigned_technician_id ? Number(form.assigned_technician_id) : null }) })
        if (form.status !== selected.status) updated = await apiFetch<MaintenanceRequest>(`/maintenance-requests/${selected.id}/status`, { method: "POST", body: JSON.stringify({ status: form.status, assigned_technician_id: form.assigned_technician_id ? Number(form.assigned_technician_id) : null }) })
        setItems((current) => current.map((item) => item.id === updated.id ? updated : item)); toast.success("Demande mise à jour")
      }
      setDialog(null)
    } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Enregistrement impossible.") } finally { setWorking(false) }
  }

  async function cancel(item: MaintenanceRequest) {
    if (!window.confirm(`Annuler la demande ${item.reference} ?`)) return
    try { const updated = await apiFetch<MaintenanceRequest>(`/maintenance-requests/${item.id}/cancel`, { method: "POST" }); setItems((current) => current.map((entry) => entry.id === updated.id ? updated : entry)); toast.success("Demande annulée") }
    catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Annulation impossible.") }
  }

  return <>
    <Header title="Demandes de maintenance" description="Création, validation, priorité, affectation, suivi du statut et annulation contrôlée." searchValue={search} onSearchChange={setSearch} searchPlaceholder="Référence, description ou équipement" actions={<><Button className="h-9" onClick={openCreate}><Plus className="mr-2 h-4 w-4" />Nouvelle demande</Button><Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button></>}/>
    <div className="mt-5 space-y-4">{error && <ErrorBanner message={error} />}<div className="grid gap-3 sm:grid-cols-3"><Kpi label="Demandes" value={items.length} icon={ClipboardList} /><Kpi label="Ouvertes" value={items.filter((item) => !["CLOSED", "RESOLVED", "CANCELLED", "REJECTED"].includes(item.status)).length} icon={ClipboardCheck} tone="amber" /><Kpi label="Affectées" value={items.filter((item) => item.assigned_technician_id !== null).length} icon={UserCheck} tone="green" /></div><Card className="overflow-hidden shadow-sm"><div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold">File des demandes</h2><p className="text-xs text-muted-foreground">{filtered.length} demande(s)</p></div><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-52"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">Tous les statuts</SelectItem>{statuses.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></div>{loading ? <div className="p-5"><LoadingState /></div> : filtered.length === 0 ? <div className="p-5"><EmptyState title="Aucune demande" description="Créez une demande ou modifiez les filtres." icon={ClipboardList} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Référence</TableHead><TableHead>Équipement</TableHead><TableHead>Description</TableHead><TableHead>Priorité</TableHead><TableHead>Statut</TableHead><TableHead>Technicien</TableHead><TableHead>Date</TableHead><TableHead /></TableRow></TableHeader><TableBody>{filtered.map((item) => { const equipment = equipmentMap.get(item.equipment_id); return <TableRow key={item.id}><TableCell className="font-semibold">{item.reference}</TableCell><TableCell><p>{equipment?.code ?? `#${item.equipment_id}`}</p><p className="text-xs text-muted-foreground">{[equipment?.brand, equipment?.model].filter(Boolean).join(" ")}</p></TableCell><TableCell className="max-w-sm"><p className="line-clamp-2">{item.description}</p></TableCell><TableCell><StatusBadge value={item.priority} /></TableCell><TableCell><StatusBadge value={item.status} /></TableCell><TableCell>{item.assigned_technician_id ? technicianMap.get(item.assigned_technician_id) ?? `#${item.assigned_technician_id}` : "Non affectée"}</TableCell><TableCell>{formatDateTime(item.submitted_at)}</TableCell><TableCell><div className="flex gap-1"><Button size="icon" variant="ghost" onClick={() => openEdit(item)}><Pencil className="h-4 w-4" /></Button>{!["CLOSED", "RESOLVED", "CANCELLED", "REJECTED"].includes(item.status) && <Button size="icon" variant="ghost" onClick={() => void cancel(item)}><Ban className="h-4 w-4 text-red-600" /></Button>}</div></TableCell></TableRow> })}</TableBody></Table></div>}</Card></div>

    <Dialog open={dialog !== null} onOpenChange={(open) => !open && setDialog(null)}><DialogContent className="sm:max-w-2xl"><form onSubmit={saveRequest}><DialogHeader><DialogTitle>{dialog === "create" ? "Nouvelle demande" : `Modifier ${selected?.reference}`}</DialogTitle><DialogDescription>Le triage MaintIA peut ensuite proposer une classification et une priorité.</DialogDescription></DialogHeader><div className="mt-5 space-y-4"><Field label="Équipement *"><Select value={form.equipment_id} disabled={dialog === "edit"} onValueChange={(value) => setForm({ ...form, equipment_id: value })}><SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{equipments.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.code} · {[item.brand, item.model].filter(Boolean).join(" ")}</SelectItem>)}</SelectContent></Select></Field><Field label="Description *"><Textarea minLength={5} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} required /></Field><div className="grid gap-4 sm:grid-cols-2"><Field label="Catégorie"><Input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} /></Field><Field label="Priorité"><Select value={form.priority} onValueChange={(value) => setForm({ ...form, priority: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="LOW">Faible</SelectItem><SelectItem value="MEDIUM">Moyenne</SelectItem><SelectItem value="HIGH">Élevée</SelectItem><SelectItem value="CRITICAL">Critique</SelectItem></SelectContent></Select></Field>{dialog === "edit" && canManage && <><Field label="Technicien"><Select value={form.assigned_technician_id || "NONE"} onValueChange={(value) => setForm({ ...form, assigned_technician_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="NONE">Non affectée</SelectItem>{technicians.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.first_name} {item.last_name}</SelectItem>)}</SelectContent></Select></Field><Field label="Statut"><Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{statuses.filter((value) => value !== "CANCELLED").map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></Field></>}</div></div><DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setDialog(null)}>Annuler</Button><Button type="submit" disabled={working || !form.equipment_id}>{working ? "Enregistrement…" : "Enregistrer"}</Button></DialogFooter></form></DialogContent></Dialog>
  </>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }
function Kpi({ label, value, icon: Icon, tone = "primary" }: { label: string; value: number; icon: typeof ClipboardList; tone?: "primary" | "amber" | "green" }) { const colors = { primary: "bg-primary/10 text-primary", amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/30", green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30" }; return <Card className="p-4 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-3xl font-black">{value}</p></div><div className={`rounded-2xl p-3 ${colors[tone]}`}><Icon className="h-5 w-5" /></div></div></Card> }
