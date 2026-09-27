"use client"

import { KeyRound, Pencil, Plus, Power, PowerOff, RefreshCcw, ShieldCheck, UserCheck, UsersRound } from "lucide-react"
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
import { ApiError, apiFetch } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { statusLabel } from "@/lib/status"
import type { OrganizationItem, User } from "@/lib/types"

const roles = ["ADMIN", "MANAGER", "TECHNICIAN", "STOCK_MANAGER", "REQUESTER"]

export function UsersContent() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [services, setServices] = useState<OrganizationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState("ALL")
  const [dialog, setDialog] = useState<"create" | "edit" | "password" | null>(null)
  const [selected, setSelected] = useState<User | null>(null)
  const [working, setWorking] = useState(false)
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "", role: "REQUESTER", service_id: "", status: "ACTIVE" })

  async function loadData() {
    setLoading(true); setError(null)
    try { const [userData, serviceData] = await Promise.all([apiFetch<User[]>("/users?limit=200"), apiFetch<OrganizationItem[]>("/services?limit=200")]); setUsers(userData); setServices(serviceData) }
    catch (caught) { setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les utilisateurs.") }
    finally { setLoading(false) }
  }
  useEffect(() => { void loadData() }, [])

  const serviceMap = useMemo(() => new Map(services.map((item) => [item.id, item.name])), [services])
  const filtered = useMemo(() => { const query = search.trim().toLowerCase(); return users.filter((item) => (!query || `${item.first_name} ${item.last_name} ${item.email}`.toLowerCase().includes(query)) && (roleFilter === "ALL" || item.role === roleFilter)) }, [roleFilter, search, users])

  function openCreate() { setSelected(null); setForm({ first_name: "", last_name: "", email: "", password: "", role: "REQUESTER", service_id: "", status: "ACTIVE" }); setDialog("create") }
  function openEdit(item: User) { setSelected(item); setForm({ first_name: item.first_name, last_name: item.last_name, email: item.email, password: "", role: item.role, service_id: item.service_id ? String(item.service_id) : "", status: item.status }); setDialog("edit") }
  function openPassword(item: User) { setSelected(item); setForm((value) => ({ ...value, password: "" })); setDialog("password") }

  async function saveUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setWorking(true)
    try {
      if (dialog === "create") {
        const created = await apiFetch<User>("/users", { method: "POST", body: JSON.stringify({ first_name: form.first_name, last_name: form.last_name, email: form.email, password: form.password, role: form.role, service_id: form.service_id ? Number(form.service_id) : null }) })
        setUsers((items) => [created, ...items]); toast.success("Compte créé")
      } else if (dialog === "edit" && selected) {
        const updated = await apiFetch<User>(`/users/${selected.id}`, { method: "PATCH", body: JSON.stringify({ first_name: form.first_name, last_name: form.last_name, role: form.role, status: form.status, service_id: form.service_id ? Number(form.service_id) : null }) })
        setUsers((items) => items.map((item) => item.id === updated.id ? updated : item)); toast.success("Compte mis à jour")
      } else if (dialog === "password" && selected) {
        await apiFetch<{ message: string }>(`/users/${selected.id}/reset-password`, { method: "POST", body: JSON.stringify({ new_password: form.password }) }); toast.success("Mot de passe réinitialisé")
      }
      setDialog(null)
    } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Opération impossible.") }
    finally { setWorking(false) }
  }

  async function toggleStatus(item: User) {
    if (item.id === currentUser?.id && item.status === "ACTIVE") { toast.error("Vous ne pouvez pas désactiver votre propre compte."); return }
    try { const endpoint = item.status === "ACTIVE" ? "deactivate" : "activate"; const updated = await apiFetch<User>(`/users/${item.id}/${endpoint}`, { method: "POST" }); setUsers((items) => items.map((entry) => entry.id === updated.id ? updated : entry)); toast.success(item.status === "ACTIVE" ? "Compte désactivé" : "Compte activé") }
    catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Opération impossible.") }
  }

  return <>
    <Header title="Utilisateurs et rôles" description="Création, modification, activation, désactivation et réinitialisation sécurisée des comptes." searchValue={search} onSearchChange={setSearch} searchPlaceholder="Nom, prénom ou email" actions={<><Button className="h-9" onClick={openCreate}><Plus className="mr-2 h-4 w-4" />Créer un compte</Button><Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button></>}/>
    <div className="mt-5 space-y-4">{error && <ErrorBanner message={error} />}<div className="grid gap-3 sm:grid-cols-3"><Kpi label="Comptes" value={users.length} icon={UsersRound} /><Kpi label="Actifs" value={users.filter((item) => item.status === "ACTIVE").length} icon={UserCheck} tone="green" /><Kpi label="Techniciens" value={users.filter((item) => item.role === "TECHNICIAN").length} icon={ShieldCheck} tone="blue" /></div><Card className="overflow-hidden shadow-sm"><div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold">Annuaire</h2><p className="text-xs text-muted-foreground">{filtered.length} compte(s)</p></div><Select value={roleFilter} onValueChange={setRoleFilter}><SelectTrigger className="w-56"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">Tous les rôles</SelectItem>{roles.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></div>{loading ? <div className="p-5"><LoadingState /></div> : filtered.length === 0 ? <div className="p-5"><EmptyState title="Aucun utilisateur" description="Créez un compte ou modifiez la recherche." icon={UsersRound} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Utilisateur</TableHead><TableHead>Rôle</TableHead><TableHead>Service</TableHead><TableHead>Statut</TableHead><TableHead>Création</TableHead><TableHead /></TableRow></TableHeader><TableBody>{filtered.map((item) => <TableRow key={item.id}><TableCell><p className="font-semibold">{item.first_name} {item.last_name}</p><p className="text-xs text-muted-foreground">{item.email}</p></TableCell><TableCell><StatusBadge value={item.role} /></TableCell><TableCell>{item.service_id ? serviceMap.get(item.service_id) ?? `#${item.service_id}` : "—"}</TableCell><TableCell><StatusBadge value={item.status} /></TableCell><TableCell>{formatDate(item.created_at)}</TableCell><TableCell><div className="flex gap-1"><Button size="icon" variant="ghost" onClick={() => openEdit(item)} title="Modifier"><Pencil className="h-4 w-4" /></Button><Button size="icon" variant="ghost" onClick={() => openPassword(item)} title="Réinitialiser le mot de passe"><KeyRound className="h-4 w-4" /></Button><Button size="icon" variant="ghost" onClick={() => void toggleStatus(item)} title={item.status === "ACTIVE" ? "Désactiver" : "Activer"}>{item.status === "ACTIVE" ? <PowerOff className="h-4 w-4 text-red-600" /> : <Power className="h-4 w-4 text-emerald-600" />}</Button></div></TableCell></TableRow>)}</TableBody></Table></div>}</Card></div>

    <Dialog open={dialog !== null} onOpenChange={(open) => !open && setDialog(null)}><DialogContent><form onSubmit={saveUser}><DialogHeader><DialogTitle>{dialog === "create" ? "Nouvel utilisateur" : dialog === "edit" ? "Modifier le compte" : "Réinitialiser le mot de passe"}</DialogTitle><DialogDescription>{dialog === "password" ? `Compte ${selected?.email}` : "Les permissions finales sont également contrôlées par le Backend."}</DialogDescription></DialogHeader>{dialog === "password" ? <div className="mt-5"><Field label="Nouveau mot de passe *"><Input type="password" minLength={8} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required /></Field></div> : <div className="mt-5 grid gap-4 sm:grid-cols-2"><Field label="Prénom *"><Input value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} required /></Field><Field label="Nom *"><Input value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} required /></Field><div className="sm:col-span-2"><Field label="Email *"><Input type="email" value={form.email} disabled={dialog === "edit"} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></Field></div>{dialog === "create" && <div className="sm:col-span-2"><Field label="Mot de passe initial *"><Input type="password" minLength={8} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required /></Field></div>}<Field label="Rôle"><Select value={form.role} onValueChange={(value) => setForm({ ...form, role: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{roles.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></Field><Field label="Service"><Select value={form.service_id || "NONE"} onValueChange={(value) => setForm({ ...form, service_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="NONE">Aucun</SelectItem>{services.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.name}</SelectItem>)}</SelectContent></Select></Field>{dialog === "edit" && <Field label="Statut"><Select value={form.status} onValueChange={(value) => setForm({ ...form, status: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ACTIVE">Actif</SelectItem><SelectItem value="INACTIVE">Inactif</SelectItem></SelectContent></Select></Field>}</div>}<DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setDialog(null)}>Annuler</Button><Button type="submit" disabled={working}>{working ? "Enregistrement…" : "Enregistrer"}</Button></DialogFooter></form></DialogContent></Dialog>
  </>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }
function Kpi({ label, value, icon: Icon, tone = "primary" }: { label: string; value: number; icon: typeof UsersRound; tone?: "primary" | "green" | "blue" }) { const colors = { primary: "bg-primary/10 text-primary", green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30", blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/30" }; return <Card className="p-4 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-3xl font-black">{value}</p></div><div className={`rounded-2xl p-3 ${colors[tone]}`}><Icon className="h-5 w-5" /></div></div></Card> }
