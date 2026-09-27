"use client"

import { Ban, CheckCircle2, CirclePlus, Clock3, Edit3, PackagePlus, Plus, RefreshCcw, Save, Trash2, Wrench } from "lucide-react"
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
import { formatDateTime, formatMoney } from "@/lib/format"
import { hasRole, permissions } from "@/lib/permissions"
import { statusLabel } from "@/lib/status"
import type { Equipment, Intervention, InterventionAction, InterventionPart, InterventionStatusHistory, MaintenanceRequest, SparePart, User } from "@/lib/types"

const statuses = ["PLANNED", "WAITING", "DIAGNOSING", "REPAIRING", "WAITING_FOR_PART", "TESTING", "COMPLETED", "CANCELLED"]

export function InterventionsContent() {
  const { user } = useAuth()
  const canCreate = hasRole(user?.role, permissions.manager)
  const canWork = hasRole(user?.role, permissions.technician)
  const [items, setItems] = useState<Intervention[]>([])
  const [equipments, setEquipments] = useState<Equipment[]>([])
  const [requests, setRequests] = useState<MaintenanceRequest[]>([])
  const [technicians, setTechnicians] = useState<User[]>([])
  const [partsCatalog, setPartsCatalog] = useState<SparePart[]>([])
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("ALL")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [working, setWorking] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selected, setSelected] = useState<Intervention | null>(null)
  const [actions, setActions] = useState<InterventionAction[]>([])
  const [usedParts, setUsedParts] = useState<InterventionPart[]>([])
  const [history, setHistory] = useState<InterventionStatusHistory[]>([])
  const [createForm, setCreateForm] = useState({ request_id: "", equipment_id: "", technician_id: "", maintenance_type: "CORRECTIVE", estimated_cost: "0" })
  const [editForm, setEditForm] = useState({ diagnosis: "", solution: "", test_result: "", actual_cost: "0", status: "PLANNED", comment: "" })
  const [actionText, setActionText] = useState("")
  const [partForm, setPartForm] = useState({ part_id: "", quantity: "1" })
  const [closeForm, setCloseForm] = useState({ diagnosis: "", solution: "", test_result: "", comment: "" })
  const [cancelReason, setCancelReason] = useState("")

  const equipmentMap = useMemo(() => new Map(equipments.map((item) => [item.id, item])), [equipments])
  const technicianMap = useMemo(() => new Map(technicians.map((item) => [item.id, `${item.first_name} ${item.last_name}`])), [technicians])
  const partMap = useMemo(() => new Map(partsCatalog.map((item) => [item.id, item])), [partsCatalog])
  const filtered = useMemo(() => { const query = search.trim().toLowerCase(); return items.filter((item) => { const equipment = equipmentMap.get(item.equipment_id); const match = !query || [item.reference, item.diagnosis, item.solution, equipment?.code].filter(Boolean).some((value) => String(value).toLowerCase().includes(query)); return match && (statusFilter === "ALL" || item.status === statusFilter) }) }, [equipmentMap, items, search, statusFilter])

  async function loadData() {
    setLoading(true); setError(null)
    try {
      const [interventionData, equipmentData, requestData, partData] = await Promise.all([
        apiFetch<Intervention[]>("/interventions?limit=200"), apiFetch<Equipment[]>("/equipments?limit=200"), apiFetch<MaintenanceRequest[]>("/maintenance-requests?limit=200"), apiFetch<SparePart[]>("/spare-parts?limit=200"),
      ])
      setItems(interventionData); setEquipments(equipmentData); setRequests(requestData); setPartsCatalog(partData)
      if (hasRole(user?.role, permissions.manager)) { try { const users = await apiFetch<User[]>("/users?limit=200"); setTechnicians(users.filter((item) => item.role === "TECHNICIAN" && item.status === "ACTIVE")) } catch { setTechnicians([]) } }
    } catch (caught) { setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les interventions.") } finally { setLoading(false) }
  }
  useEffect(() => { void loadData() }, [user?.role])

  async function createItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setWorking(true)
    try {
      const created = await apiFetch<Intervention>("/interventions", { method: "POST", body: JSON.stringify({ request_id: createForm.request_id ? Number(createForm.request_id) : null, equipment_id: Number(createForm.equipment_id), technician_id: Number(createForm.technician_id), maintenance_type: createForm.maintenance_type, estimated_cost: Number(createForm.estimated_cost || 0) }) })
      setItems((current) => [created, ...current]); setCreateOpen(false); toast.success("Intervention créée")
    } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Création impossible.") } finally { setWorking(false) }
  }

  async function openDetail(item: Intervention) {
    setSelected(item); setEditForm({ diagnosis: item.diagnosis ?? "", solution: item.solution ?? "", test_result: item.test_result ?? "", actual_cost: String(item.actual_cost ?? 0), status: item.status, comment: "" }); setCloseForm({ diagnosis: item.diagnosis ?? "", solution: item.solution ?? "", test_result: item.test_result ?? "", comment: "" }); setDetailOpen(true)
    try {
      const [actionData, partData, historyData] = await Promise.all([apiFetch<InterventionAction[]>(`/interventions/${item.id}/actions`), apiFetch<InterventionPart[]>(`/interventions/${item.id}/parts`), apiFetch<InterventionStatusHistory[]>(`/interventions/${item.id}/status-history`)])
      setActions(actionData); setUsedParts(partData); setHistory(historyData)
    } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Détails incomplets.") }
  }

  async function saveDetails() {
    if (!selected) return; setWorking(true)
    try {
      let updated = await apiFetch<Intervention>(`/interventions/${selected.id}`, { method: "PATCH", body: JSON.stringify({ diagnosis: editForm.diagnosis || null, solution: editForm.solution || null, test_result: editForm.test_result || null, actual_cost: Number(editForm.actual_cost || 0) }) })
      if (editForm.status !== selected.status && !["COMPLETED", "CANCELLED"].includes(editForm.status)) updated = await apiFetch<Intervention>(`/interventions/${selected.id}/status`, { method: "POST", body: JSON.stringify({ status: editForm.status, comment: editForm.comment || null }) })
      setSelected(updated); setItems((current) => current.map((item) => item.id === updated.id ? updated : item)); toast.success("Intervention mise à jour")
      const historyData = await apiFetch<InterventionStatusHistory[]>(`/interventions/${selected.id}/status-history`); setHistory(historyData)
    } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Mise à jour impossible.") } finally { setWorking(false) }
  }

  async function addAction() {
    if (!selected || actionText.trim().length < 3) return; setWorking(true)
    try { const created = await apiFetch<InterventionAction>(`/interventions/${selected.id}/actions`, { method: "POST", body: JSON.stringify({ description: actionText.trim() }) }); setActions((current) => [...current, created]); setActionText(""); toast.success("Action ajoutée") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Ajout impossible.") } finally { setWorking(false) }
  }

  async function editAction(action: InterventionAction) {
    const description = window.prompt("Modifier l’action", action.description); if (!description || description.trim().length < 3 || !selected) return
    try { const updated = await apiFetch<InterventionAction>(`/interventions/${selected.id}/actions/${action.id}`, { method: "PATCH", body: JSON.stringify({ description: description.trim() }) }); setActions((current) => current.map((item) => item.id === updated.id ? updated : item)); toast.success("Action modifiée") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Modification impossible.") }
  }

  async function deleteAction(action: InterventionAction) {
    if (!selected || !window.confirm("Supprimer cette action ?")) return
    try { await apiFetch<{ message: string }>(`/interventions/${selected.id}/actions/${action.id}`, { method: "DELETE" }); setActions((current) => current.filter((item) => item.id !== action.id)); toast.success("Action supprimée") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Suppression impossible.") }
  }

  async function addPart() {
    if (!selected || !partForm.part_id) return; setWorking(true)
    try { const created = await apiFetch<InterventionPart>(`/interventions/${selected.id}/parts`, { method: "POST", body: JSON.stringify({ part_id: Number(partForm.part_id), quantity: Number(partForm.quantity) }) }); setUsedParts((current) => [...current, created]); setPartForm({ part_id: "", quantity: "1" }); toast.success("Pièce sortie du stock") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Sortie impossible.") } finally { setWorking(false) }
  }

  async function editPart(link: InterventionPart) {
    if (!selected) return; const quantity = window.prompt("Nouvelle quantité", String(link.quantity)); if (!quantity || Number(quantity) <= 0) return
    try { const updated = await apiFetch<InterventionPart>(`/interventions/${selected.id}/parts/${link.id}`, { method: "PATCH", body: JSON.stringify({ quantity: Number(quantity) }) }); setUsedParts((current) => current.map((item) => item.id === updated.id ? updated : item)); toast.success("Quantité et stock ajustés") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Modification impossible.") }
  }

  async function deletePart(link: InterventionPart) {
    if (!selected || !window.confirm("Retirer cette pièce de l’intervention et la retourner au stock ?")) return
    try { await apiFetch<{ message: string }>(`/interventions/${selected.id}/parts/${link.id}`, { method: "DELETE" }); setUsedParts((current) => current.filter((item) => item.id !== link.id)); toast.success("Pièce retournée au stock") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Retour impossible.") }
  }

  async function closeIntervention() {
    if (!selected) return; setWorking(true)
    try { const updated = await apiFetch<Intervention>(`/interventions/${selected.id}/close`, { method: "POST", body: JSON.stringify(closeForm) }); setSelected(updated); setItems((current) => current.map((item) => item.id === updated.id ? updated : item)); setEditForm((form) => ({ ...form, status: updated.status })); toast.success("Intervention clôturée") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Clôture impossible.") } finally { setWorking(false) }
  }

  async function cancelIntervention() {
    if (!selected || cancelReason.trim().length < 3) return; setWorking(true)
    try { const updated = await apiFetch<Intervention>(`/interventions/${selected.id}/cancel`, { method: "POST", body: JSON.stringify({ reason: cancelReason.trim() }) }); setSelected(updated); setItems((current) => current.map((item) => item.id === updated.id ? updated : item)); setEditForm((form) => ({ ...form, status: updated.status })); setCancelReason(""); toast.success("Intervention annulée") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Annulation impossible.") } finally { setWorking(false) }
  }

  return <>
    <Header title="Interventions" description="Cockpit technique complet : diagnostic, statut, actions, pièces, historique, clôture et annulation contrôlées." searchValue={search} onSearchChange={setSearch} searchPlaceholder="Référence, équipement, diagnostic ou solution" actions={<>{canCreate && <Dialog open={createOpen} onOpenChange={setCreateOpen}><DialogTrigger asChild><Button className="h-9"><Plus className="mr-2 h-4 w-4" />Créer</Button></DialogTrigger><DialogContent><form onSubmit={createItem}><DialogHeader><DialogTitle>Nouvelle intervention</DialogTitle><DialogDescription>Affectez un technicien et un équipement.</DialogDescription></DialogHeader><div className="mt-5 space-y-4"><Field label="Demande associée"><Select value={createForm.request_id || "NONE"} onValueChange={(value) => setCreateForm({ ...createForm, request_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="NONE">Aucune</SelectItem>{requests.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.reference}</SelectItem>)}</SelectContent></Select></Field><Field label="Équipement *"><Select value={createForm.equipment_id} onValueChange={(value) => setCreateForm({ ...createForm, equipment_id: value })}><SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{equipments.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.code} · {[item.brand, item.model].filter(Boolean).join(" ")}</SelectItem>)}</SelectContent></Select></Field><Field label="Technicien *"><Select value={createForm.technician_id} onValueChange={(value) => setCreateForm({ ...createForm, technician_id: value })}><SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{technicians.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.first_name} {item.last_name}</SelectItem>)}</SelectContent></Select></Field><div className="grid gap-4 sm:grid-cols-2"><Field label="Type"><Select value={createForm.maintenance_type} onValueChange={(value) => setCreateForm({ ...createForm, maintenance_type: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="CORRECTIVE">Corrective</SelectItem><SelectItem value="PREVENTIVE">Préventive</SelectItem></SelectContent></Select></Field><Field label="Coût estimé (MAD)"><Input type="number" min="0" step="0.01" value={createForm.estimated_cost} onChange={(event) => setCreateForm({ ...createForm, estimated_cost: event.target.value })} /></Field></div></div><DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Annuler</Button><Button type="submit" disabled={working || !createForm.equipment_id || !createForm.technician_id}>Créer</Button></DialogFooter></form></DialogContent></Dialog>}<Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button></>}/>
    <div className="mt-5 space-y-4">{error && <ErrorBanner message={error} />}<div className="grid gap-3 sm:grid-cols-3"><Kpi label="Total" value={items.length} icon={Wrench} /><Kpi label="Actives" value={items.filter((item) => !["COMPLETED", "CANCELLED"].includes(item.status)).length} icon={Clock3} tone="amber" /><Kpi label="Terminées" value={items.filter((item) => item.status === "COMPLETED").length} icon={CheckCircle2} tone="green" /></div><Card className="overflow-hidden shadow-sm"><div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold">Suivi opérationnel</h2><p className="text-xs text-muted-foreground">{filtered.length} intervention(s)</p></div><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-52"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">Tous les statuts</SelectItem>{statuses.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></div>{loading ? <div className="p-5"><LoadingState /></div> : filtered.length === 0 ? <div className="p-5"><EmptyState title="Aucune intervention" description="Créez ou modifiez les filtres." icon={Wrench} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Référence</TableHead><TableHead>Équipement</TableHead><TableHead>Technicien</TableHead><TableHead>Type</TableHead><TableHead>Statut</TableHead><TableHead>Diagnostic</TableHead><TableHead>Coût</TableHead><TableHead /></TableRow></TableHeader><TableBody>{filtered.map((item) => { const equipment = equipmentMap.get(item.equipment_id); return <TableRow key={item.id}><TableCell className="font-semibold">{item.reference}</TableCell><TableCell><p>{equipment?.code ?? `#${item.equipment_id}`}</p><p className="text-xs text-muted-foreground">{[equipment?.brand, equipment?.model].filter(Boolean).join(" ")}</p></TableCell><TableCell>{technicianMap.get(item.technician_id) ?? `#${item.technician_id}`}</TableCell><TableCell><StatusBadge value={item.maintenance_type} /></TableCell><TableCell><StatusBadge value={item.status} /></TableCell><TableCell className="max-w-64"><p className="line-clamp-2">{item.diagnosis || "Non renseigné"}</p></TableCell><TableCell>{formatMoney(item.actual_cost)}</TableCell><TableCell><Button size="sm" variant="outline" onClick={() => void openDetail(item)}>Ouvrir</Button></TableCell></TableRow> })}</TableBody></Table></div>}</Card></div>

    <Dialog open={detailOpen} onOpenChange={setDetailOpen}><DialogContent className="max-h-[94vh] overflow-y-auto sm:max-w-5xl"><DialogHeader><DialogTitle>{selected?.reference}</DialogTitle><DialogDescription>Équipement {selected ? equipmentMap.get(selected.equipment_id)?.code ?? selected.equipment_id : "—"} · Statut {selected?.status}</DialogDescription></DialogHeader>{selected && <Tabs defaultValue="details" className="mt-2"><TabsList className="grid h-auto grid-cols-3 gap-1 sm:grid-cols-6"><TabsTrigger value="details">Détails</TabsTrigger><TabsTrigger value="actions">Actions</TabsTrigger><TabsTrigger value="parts">Pièces</TabsTrigger><TabsTrigger value="history">Historique</TabsTrigger><TabsTrigger value="close">Clôturer</TabsTrigger><TabsTrigger value="cancel">Annuler</TabsTrigger></TabsList><TabsContent value="details" className="space-y-4 pt-4"><div className="grid gap-4 sm:grid-cols-2"><Field label="Diagnostic"><Textarea value={editForm.diagnosis} onChange={(event) => setEditForm({ ...editForm, diagnosis: event.target.value })} /></Field><Field label="Solution"><Textarea value={editForm.solution} onChange={(event) => setEditForm({ ...editForm, solution: event.target.value })} /></Field><Field label="Résultat des tests"><Input value={editForm.test_result} onChange={(event) => setEditForm({ ...editForm, test_result: event.target.value })} /></Field><Field label="Coût réel (MAD)"><Input type="number" min="0" step="0.01" value={editForm.actual_cost} onChange={(event) => setEditForm({ ...editForm, actual_cost: event.target.value })} /></Field><Field label="Statut"><Select value={editForm.status} onValueChange={(value) => setEditForm({ ...editForm, status: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{statuses.filter((value) => !["COMPLETED", "CANCELLED"].includes(value)).map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></Field><Field label="Commentaire"><Input value={editForm.comment} onChange={(event) => setEditForm({ ...editForm, comment: event.target.value })} /></Field></div><Button onClick={() => void saveDetails()} disabled={!canWork || working}><Save className="mr-2 h-4 w-4" />Enregistrer</Button></TabsContent><TabsContent value="actions" className="space-y-4 pt-4"><div className="flex gap-2"><Input value={actionText} onChange={(event) => setActionText(event.target.value)} placeholder="Décrire l’action technique réalisée…" /><Button onClick={() => void addAction()} disabled={!canWork || working}><CirclePlus className="mr-2 h-4 w-4" />Ajouter</Button></div><div className="space-y-2">{actions.length === 0 ? <EmptyState title="Aucune action" description="Consignez les opérations réalisées." icon={Edit3} /> : actions.map((action) => <div key={action.id} className="flex items-start justify-between gap-3 rounded-xl border p-3"><div><p className="text-sm">{action.description}</p><p className="mt-1 text-[10px] text-muted-foreground">{formatDateTime(action.performed_at)} · Utilisateur #{action.performed_by_id}</p></div><div className="flex gap-1"><Button size="icon" variant="ghost" onClick={() => void editAction(action)}><Edit3 className="h-4 w-4" /></Button><Button size="icon" variant="ghost" onClick={() => void deleteAction(action)}><Trash2 className="h-4 w-4 text-red-600" /></Button></div></div>)}</div></TabsContent><TabsContent value="parts" className="space-y-4 pt-4"><div className="grid gap-2 sm:grid-cols-[1fr_120px_auto]"><Select value={partForm.part_id} onValueChange={(value) => setPartForm({ ...partForm, part_id: value })}><SelectTrigger><SelectValue placeholder="Sélectionner une pièce" /></SelectTrigger><SelectContent>{partsCatalog.filter((part) => part.active).map((part) => <SelectItem key={part.id} value={String(part.id)}>{part.code} · {part.name} · stock {part.quantity}</SelectItem>)}</SelectContent></Select><Input type="number" min="1" value={partForm.quantity} onChange={(event) => setPartForm({ ...partForm, quantity: event.target.value })} /><Button onClick={() => void addPart()} disabled={!canWork || !partForm.part_id || working}><PackagePlus className="mr-2 h-4 w-4" />Sortir</Button></div><div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Pièce</TableHead><TableHead>Quantité</TableHead><TableHead>Prix unitaire</TableHead><TableHead>Total</TableHead><TableHead /></TableRow></TableHeader><TableBody>{usedParts.map((link) => { const part = partMap.get(link.part_id); return <TableRow key={link.id}><TableCell><p className="font-medium">{part?.code ?? `#${link.part_id}`}</p><p className="text-xs text-muted-foreground">{part?.name}</p></TableCell><TableCell>{link.quantity}</TableCell><TableCell>{formatMoney(link.unit_price)}</TableCell><TableCell>{formatMoney(Number(link.unit_price) * link.quantity)}</TableCell><TableCell><div className="flex gap-1"><Button size="icon" variant="ghost" onClick={() => void editPart(link)}><Edit3 className="h-4 w-4" /></Button><Button size="icon" variant="ghost" onClick={() => void deletePart(link)}><Trash2 className="h-4 w-4 text-red-600" /></Button></div></TableCell></TableRow> })}</TableBody></Table></div></TabsContent><TabsContent value="history" className="pt-4"><div className="space-y-3">{history.map((entry) => <div key={entry.id} className="flex gap-3 rounded-xl border p-3"><div className="mt-1 h-2 w-2 rounded-full bg-primary" /><div><div className="flex items-center gap-2"><StatusBadge value={entry.old_status} /><span>→</span><StatusBadge value={entry.new_status} /></div><p className="mt-1 text-xs text-muted-foreground">{formatDateTime(entry.changed_at)} · {entry.comment || "Sans commentaire"}</p></div></div>)}</div></TabsContent><TabsContent value="close" className="space-y-4 pt-4"><div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/20 dark:text-emerald-200">La clôture remet l’équipement en service et exige un diagnostic, une solution et un résultat de test.</div><Field label="Diagnostic *"><Textarea value={closeForm.diagnosis} onChange={(event) => setCloseForm({ ...closeForm, diagnosis: event.target.value })} /></Field><Field label="Solution *"><Textarea value={closeForm.solution} onChange={(event) => setCloseForm({ ...closeForm, solution: event.target.value })} /></Field><Field label="Résultat du test *"><Textarea value={closeForm.test_result} onChange={(event) => setCloseForm({ ...closeForm, test_result: event.target.value })} /></Field><Field label="Commentaire"><Input value={closeForm.comment} onChange={(event) => setCloseForm({ ...closeForm, comment: event.target.value })} /></Field><Button onClick={() => void closeIntervention()} disabled={!canWork || working || closeForm.diagnosis.length < 3 || closeForm.solution.length < 3 || closeForm.test_result.length < 2}><CheckCircle2 className="mr-2 h-4 w-4" />Clôturer l’intervention</Button></TabsContent><TabsContent value="cancel" className="space-y-4 pt-4"><Field label="Motif d’annulation *"><Textarea value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} /></Field><Button variant="destructive" onClick={() => void cancelIntervention()} disabled={!canWork || working || cancelReason.trim().length < 3}><Ban className="mr-2 h-4 w-4" />Annuler l’intervention</Button></TabsContent></Tabs>}</DialogContent></Dialog>
  </>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }
function Kpi({ label, value, icon: Icon, tone = "primary" }: { label: string; value: number; icon: typeof Wrench; tone?: "primary" | "amber" | "green" }) { const colors = { primary: "bg-primary/10 text-primary", amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/30", green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30" }; return <Card className="p-4 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-3xl font-black">{value}</p></div><div className={`rounded-2xl p-3 ${colors[tone]}`}><Icon className="h-5 w-5" /></div></div></Card> }
