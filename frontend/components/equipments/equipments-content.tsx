"use client"

import { Archive, Boxes, History, Pencil, Plus, Power, RefreshCcw, UserPlus } from "lucide-react"
import Link from "next/link"
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ApiError, apiFetch } from "@/lib/api"
import { formatDate, formatDateTime } from "@/lib/format"
import { hasRole, permissions } from "@/lib/permissions"
import { statusLabel } from "@/lib/status"
import type { Equipment, EquipmentAssignment, EquipmentCategory, EquipmentKpi, OrganizationItem, User } from "@/lib/types"

const equipmentStatuses = ["IN_SERVICE", "IN_FAILURE", "IN_MAINTENANCE", "WAITING_PART", "OUT_OF_SERVICE", "REFORMED", "ARCHIVED"]
const blank = { code: "", category_id: "", brand: "", model: "", serial_number: "", acquisition_date: "", commissioning_date: "", status: "IN_SERVICE", location_id: "", current_service_id: "", warranty_end_date: "", notes: "" }

export function EquipmentsContent() {
  const { user } = useAuth()
  const canManage = hasRole(user?.role, permissions.manager)
  const [items, setItems] = useState<Equipment[]>([])
  const [categories, setCategories] = useState<EquipmentCategory[]>([])
  const [services, setServices] = useState<OrganizationItem[]>([])
  const [locations, setLocations] = useState<OrganizationItem[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("ALL")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [working, setWorking] = useState(false)
  const [editorOpen, setEditorOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selected, setSelected] = useState<Equipment | null>(null)
  const [form, setForm] = useState(blank)
  const [assignments, setAssignments] = useState<EquipmentAssignment[]>([])
  const [historyData, setHistoryData] = useState<unknown>(null)
  const [kpi, setKpi] = useState<EquipmentKpi | null>(null)
  const [assignmentForm, setAssignmentForm] = useState({ user_id: "", service_id: "", comment: "" })

  const categoryMap = useMemo(() => new Map(categories.map((item) => [item.id, item.name])), [categories])
  const serviceMap = useMemo(() => new Map(services.map((item) => [item.id, item.name])), [services])
  const locationMap = useMemo(() => new Map(locations.map((item) => [item.id, item.name])), [locations])
  const userMap = useMemo(() => new Map(users.map((item) => [item.id, `${item.first_name} ${item.last_name}`])), [users])
  const filtered = useMemo(() => { const query = search.trim().toLowerCase(); return items.filter((item) => { const match = !query || [item.code, item.brand, item.model, item.serial_number].filter(Boolean).some((value) => String(value).toLowerCase().includes(query)); return match && (statusFilter === "ALL" || item.status === statusFilter) }) }, [items, search, statusFilter])

  async function loadData() {
    setLoading(true); setError(null)
    try {
      const base = await Promise.all([apiFetch<Equipment[]>("/equipments?limit=200"), apiFetch<EquipmentCategory[]>("/equipment-categories"), apiFetch<OrganizationItem[]>("/services?limit=200"), apiFetch<OrganizationItem[]>("/locations?limit=200")])
      setItems(base[0]); setCategories(base[1]); setServices(base[2]); setLocations(base[3])
      if (canManage) { try { setUsers(await apiFetch<User[]>("/users?limit=200")) } catch { setUsers([]) } }
    } catch (caught) { setError(caught instanceof ApiError ? caught.detail : "Impossible de charger le parc.") } finally { setLoading(false) }
  }
  useEffect(() => { void loadData() }, [canManage])

  function openCreate() { setSelected(null); setForm(blank); setEditorOpen(true) }
  function openEdit(item: Equipment) { setSelected(item); setForm({ code: item.code, category_id: String(item.category_id), brand: item.brand ?? "", model: item.model ?? "", serial_number: item.serial_number ?? "", acquisition_date: item.acquisition_date ?? "", commissioning_date: item.commissioning_date ?? "", status: item.status, location_id: item.location_id ? String(item.location_id) : "", current_service_id: item.current_service_id ? String(item.current_service_id) : "", warranty_end_date: item.warranty_end_date ?? "", notes: item.notes ?? "" }); setEditorOpen(true) }

  async function saveEquipment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setWorking(true)
    const payload = { category_id: Number(form.category_id), brand: form.brand || null, model: form.model || null, serial_number: form.serial_number || null, acquisition_date: form.acquisition_date || null, commissioning_date: form.commissioning_date || null, status: form.status, location_id: form.location_id ? Number(form.location_id) : null, current_service_id: form.current_service_id ? Number(form.current_service_id) : null, warranty_end_date: form.warranty_end_date || null, notes: form.notes || null }
    try {
      if (selected) { const updated = await apiFetch<Equipment>(`/equipments/${selected.id}`, { method: "PATCH", body: JSON.stringify(payload) }); setItems((current) => current.map((item) => item.id === updated.id ? updated : item)); toast.success("Équipement mis à jour") }
      else { const created = await apiFetch<Equipment>("/equipments", { method: "POST", body: JSON.stringify({ code: form.code, ...payload }) }); setItems((current) => [created, ...current]); toast.success("Équipement créé") }
      setEditorOpen(false)
    } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Enregistrement impossible.") } finally { setWorking(false) }
  }

  async function openDetail(item: Equipment) {
    setSelected(item); setDetailOpen(true); setAssignments([]); setHistoryData(null); setKpi(null)
    const [assignmentResult, historyResult, kpiResult] = await Promise.allSettled([apiFetch<EquipmentAssignment[]>(`/equipments/${item.id}/assignments`), apiFetch<unknown>(`/equipments/${item.id}/history`), apiFetch<EquipmentKpi>(`/kpi/equipments/${item.id}`)])
    if (assignmentResult.status === "fulfilled") setAssignments(assignmentResult.value)
    if (historyResult.status === "fulfilled") setHistoryData(historyResult.value)
    if (kpiResult.status === "fulfilled") setKpi(kpiResult.value)
  }

  async function assignEquipment() {
    if (!selected || (!assignmentForm.user_id && !assignmentForm.service_id)) return
    try { const created = await apiFetch<EquipmentAssignment>(`/equipments/${selected.id}/assignments`, { method: "POST", body: JSON.stringify({ user_id: assignmentForm.user_id ? Number(assignmentForm.user_id) : null, service_id: assignmentForm.service_id ? Number(assignmentForm.service_id) : null, comment: assignmentForm.comment || null }) }); setAssignments((current) => [created, ...current]); setAssignmentForm({ user_id: "", service_id: "", comment: "" }); toast.success("Affectation enregistrée") }
    catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Affectation impossible.") }
  }

  async function archive(item: Equipment) { if (!window.confirm(`Archiver ${item.code} ?`)) return; try { await apiFetch<{ message: string }>(`/equipments/${item.id}/archive`, { method: "POST" }); setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, archived: true, status: "ARCHIVED" } : entry)); toast.success("Équipement archivé") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Archivage impossible.") } }
  async function activate(item: Equipment) { try { await apiFetch<{ message: string }>(`/equipments/${item.id}/activate`, { method: "POST" }); setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, archived: false, status: "IN_SERVICE" } : entry)); toast.success("Équipement réactivé") } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Réactivation impossible.") } }

  return <>
    <Header title="Parc informatique" description="Inventaire, cycle de vie, affectations, historique, KPI et accès direct aux prévisions de panne." searchValue={search} onSearchChange={setSearch} searchPlaceholder="Code, marque, modèle ou numéro de série" actions={<>{canManage && <Button className="h-9" onClick={openCreate}><Plus className="mr-2 h-4 w-4" />Ajouter</Button>}<Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button></>}/>
    <div className="mt-5 space-y-4">{error && <ErrorBanner message={error} />}<div className="grid gap-3 sm:grid-cols-4"><Kpi label="Équipements" value={items.length} /><Kpi label="En service" value={items.filter((item) => item.status === "IN_SERVICE").length} tone="green" /><Kpi label="En panne" value={items.filter((item) => item.status === "IN_FAILURE").length} tone="red" /><Kpi label="Archivés" value={items.filter((item) => item.archived).length} tone="slate" /></div><Card className="overflow-hidden shadow-sm"><div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold">Inventaire</h2><p className="text-xs text-muted-foreground">{filtered.length} équipement(s) affiché(s)</p></div><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-52"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">Tous les statuts</SelectItem>{equipmentStatuses.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></div>{loading ? <div className="p-5"><LoadingState /></div> : filtered.length === 0 ? <div className="p-5"><EmptyState title="Aucun équipement" description="Ajoutez un équipement ou modifiez les filtres." icon={Boxes} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Équipement</TableHead><TableHead>Catégorie</TableHead><TableHead>Statut</TableHead><TableHead>Service</TableHead><TableHead>Localisation</TableHead><TableHead>Mise en service</TableHead><TableHead /></TableRow></TableHeader><TableBody>{filtered.map((item) => <TableRow key={item.id}><TableCell><p className="font-semibold">{item.code}</p><p className="text-xs text-muted-foreground">{[item.brand, item.model].filter(Boolean).join(" ") || "Marque / modèle non renseignés"}</p></TableCell><TableCell>{categoryMap.get(item.category_id) ?? `#${item.category_id}`}</TableCell><TableCell><StatusBadge value={item.status} /></TableCell><TableCell>{item.current_service_id ? serviceMap.get(item.current_service_id) ?? `#${item.current_service_id}` : "—"}</TableCell><TableCell>{item.location_id ? locationMap.get(item.location_id) ?? `#${item.location_id}` : "—"}</TableCell><TableCell>{formatDate(item.commissioning_date)}</TableCell><TableCell><div className="flex gap-1"><Button size="sm" variant="outline" onClick={() => void openDetail(item)}>Détails</Button>{canManage && <Button size="icon" variant="ghost" onClick={() => openEdit(item)}><Pencil className="h-4 w-4" /></Button>}{canManage && (item.archived ? <Button size="icon" variant="ghost" onClick={() => void activate(item)}><Power className="h-4 w-4 text-emerald-600" /></Button> : <Button size="icon" variant="ghost" onClick={() => void archive(item)}><Archive className="h-4 w-4 text-red-600" /></Button>)}</div></TableCell></TableRow>)}</TableBody></Table></div>}</Card></div>

    <Dialog open={editorOpen} onOpenChange={setEditorOpen}><DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl"><form onSubmit={saveEquipment}><DialogHeader><DialogTitle>{selected ? `Modifier ${selected.code}` : "Nouvel équipement"}</DialogTitle><DialogDescription>Les identifiants techniques sont conservés dans PostgreSQL.</DialogDescription></DialogHeader><div className="mt-5 grid gap-4 sm:grid-cols-2"><Field label="Code *"><Input value={form.code} disabled={Boolean(selected)} onChange={(event) => setForm({ ...form, code: event.target.value })} required /></Field><Field label="Catégorie *"><Select value={form.category_id} onValueChange={(value) => setForm({ ...form, category_id: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{categories.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Marque"><Input value={form.brand} onChange={(event) => setForm({ ...form, brand: event.target.value })} /></Field><Field label="Modèle"><Input value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} /></Field><Field label="Numéro de série"><Input value={form.serial_number} onChange={(event) => setForm({ ...form, serial_number: event.target.value })} /></Field><Field label="Statut"><Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{equipmentStatuses.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></Field><Field label="Date acquisition"><Input type="date" value={form.acquisition_date} onChange={(event) => setForm({ ...form, acquisition_date: event.target.value })} /></Field><Field label="Mise en service"><Input type="date" value={form.commissioning_date} onChange={(event) => setForm({ ...form, commissioning_date: event.target.value })} /></Field><Field label="Fin garantie"><Input type="date" value={form.warranty_end_date} onChange={(event) => setForm({ ...form, warranty_end_date: event.target.value })} /></Field><Field label="Service"><Select value={form.current_service_id || "NONE"} onValueChange={(value) => setForm({ ...form, current_service_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="NONE">Aucun</SelectItem>{services.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.name}</SelectItem>)}</SelectContent></Select></Field><Field label="Localisation"><Select value={form.location_id || "NONE"} onValueChange={(value) => setForm({ ...form, location_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="NONE">Aucune</SelectItem>{locations.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.name}</SelectItem>)}</SelectContent></Select></Field><div className="sm:col-span-2"><Field label="Notes"><Textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></Field></div></div><DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setEditorOpen(false)}>Annuler</Button><Button type="submit" disabled={working || !form.category_id}>{working ? "Enregistrement…" : "Enregistrer"}</Button></DialogFooter></form></DialogContent></Dialog>

    <Dialog open={detailOpen} onOpenChange={setDetailOpen}><DialogContent className="max-h-[94vh] overflow-y-auto sm:max-w-5xl"><DialogHeader><DialogTitle>{selected?.code}</DialogTitle><DialogDescription>{[selected?.brand, selected?.model, selected?.serial_number].filter(Boolean).join(" · ")}</DialogDescription></DialogHeader>{selected && <Tabs defaultValue="overview"><TabsList className="grid h-auto grid-cols-2 gap-1 sm:grid-cols-4"><TabsTrigger value="overview">Vue générale</TabsTrigger><TabsTrigger value="assignments">Affectations</TabsTrigger><TabsTrigger value="history">Historique</TabsTrigger><TabsTrigger value="intelligence">KPI & IA</TabsTrigger></TabsList><TabsContent value="overview" className="grid gap-3 pt-4 sm:grid-cols-2 xl:grid-cols-4"><Info label="Statut" value={statusLabel(selected.status)} /><Info label="Catégorie" value={categoryMap.get(selected.category_id) ?? `#${selected.category_id}`} /><Info label="Service" value={selected.current_service_id ? serviceMap.get(selected.current_service_id) ?? `#${selected.current_service_id}` : "—"} /><Info label="Localisation" value={selected.location_id ? locationMap.get(selected.location_id) ?? `#${selected.location_id}` : "—"} /><Info label="Acquisition" value={formatDate(selected.acquisition_date)} /><Info label="Mise en service" value={formatDate(selected.commissioning_date)} /><Info label="Fin garantie" value={formatDate(selected.warranty_end_date)} /><Info label="Archive" value={selected.archived ? "Oui" : "Non"} /><div className="sm:col-span-2 xl:col-span-4 rounded-2xl border p-4"><p className="text-xs text-muted-foreground">Notes</p><p className="mt-2 text-sm">{selected.notes || "Aucune note."}</p></div></TabsContent><TabsContent value="assignments" className="space-y-4 pt-4">{canManage && <Card className="p-4"><div className="grid gap-3 sm:grid-cols-[1fr_1fr_1.2fr_auto]"><Select value={assignmentForm.user_id || "NONE"} onValueChange={(value) => setAssignmentForm({ ...assignmentForm, user_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue placeholder="Utilisateur" /></SelectTrigger><SelectContent><SelectItem value="NONE">Aucun utilisateur</SelectItem>{users.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.first_name} {item.last_name}</SelectItem>)}</SelectContent></Select><Select value={assignmentForm.service_id || "NONE"} onValueChange={(value) => setAssignmentForm({ ...assignmentForm, service_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue placeholder="Service" /></SelectTrigger><SelectContent><SelectItem value="NONE">Aucun service</SelectItem>{services.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.name}</SelectItem>)}</SelectContent></Select><Input placeholder="Commentaire" value={assignmentForm.comment} onChange={(event) => setAssignmentForm({ ...assignmentForm, comment: event.target.value })} /><Button onClick={() => void assignEquipment()}><UserPlus className="mr-2 h-4 w-4" />Affecter</Button></div></Card>}<div className="space-y-2">{assignments.length === 0 ? <EmptyState title="Aucune affectation" description="Affectez l’équipement à un utilisateur ou un service." icon={UserPlus} /> : assignments.map((item) => <div key={item.id} className="rounded-xl border p-3"><div className="flex items-center justify-between"><p className="font-medium">{item.user_id ? userMap.get(item.user_id) ?? `Utilisateur #${item.user_id}` : item.service_id ? serviceMap.get(item.service_id) ?? `Service #${item.service_id}` : "Affectation générale"}</p><StatusBadge value={item.is_active ? "ACTIVE" : "INACTIVE"} /></div><p className="mt-1 text-xs text-muted-foreground">{formatDateTime(item.assigned_at)} · {item.comment || "Sans commentaire"}</p></div>)}</div></TabsContent><TabsContent value="history" className="pt-4"><Card className="p-4"><div className="mb-3 flex items-center gap-2"><History className="h-4 w-4 text-primary" /><h3 className="font-semibold">Cycle de vie consolidé</h3></div><pre className="max-h-[55vh] overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-4 text-xs text-slate-100">{historyData ? JSON.stringify(historyData, null, 2) : "Aucun historique disponible."}</pre></Card></TabsContent><TabsContent value="intelligence" className="space-y-4 pt-4">{kpi && <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Info label="Interventions" value={String(kpi.total_interventions)} /><Info label="Correctives" value={String(kpi.corrective_interventions)} /><Info label="Préventives" value={String(kpi.preventive_interventions)} /><Info label="Coût total" value={`${kpi.total_actual_cost.toLocaleString("fr-FR")} MAD`} /><Info label="MTTR" value={kpi.mttr_hours === null ? "—" : `${kpi.mttr_hours.toFixed(2)} h`} /><Info label="MTBF" value={kpi.mtbf_hours === null ? "—" : `${kpi.mtbf_hours.toFixed(2)} h`} /><Info label="Prochain préventif" value={formatDate(kpi.next_preventive_due_date)} /><Info label="Plans actifs" value={String(kpi.active_preventive_plans)} /></div>}<div className="flex flex-wrap gap-2"><Button asChild><Link href={`/forecasts?equipment=${selected.id}`}>Ouvrir les prévisions</Link></Button><Button asChild variant="outline"><Link href="/ai">Demander à MaintIA</Link></Button><Button asChild variant="outline"><Link href="/preventive">Plan préventif</Link></Button></div></TabsContent></Tabs>}</DialogContent></Dialog>
  </>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }
function Kpi({ label, value, tone = "primary" }: { label: string; value: number; tone?: "primary" | "green" | "red" | "slate" }) { const colors = { primary: "text-primary", green: "text-emerald-600", red: "text-red-600", slate: "text-slate-500" }; return <Card className="p-4"><p className="text-xs text-muted-foreground">{label}</p><p className={`mt-1 text-3xl font-black ${colors[tone]}`}>{value.toLocaleString("fr-FR")}</p></Card> }
function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-2xl border bg-secondary/20 p-4"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></div> }
