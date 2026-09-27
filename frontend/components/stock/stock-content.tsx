"use client"

import { AlertTriangle, Boxes, Edit3, PackageCheck, PackageOpen, Plus, RefreshCcw, TrendingDown } from "lucide-react"
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
import type { Intervention, SparePart, StockAlert, StockAlertsResponse, StockMovement, StockSummary } from "@/lib/types"

const movementTypes = ["IN", "OUT", "RETURN", "ADJUSTMENT_POSITIVE", "ADJUSTMENT_NEGATIVE", "INVENTORY"]

export function StockContent() {
  const { user } = useAuth()
  const canManage = hasRole(user?.role, permissions.stock)
  const [parts, setParts] = useState<SparePart[]>([])
  const [movements, setMovements] = useState<StockMovement[]>([])
  const [interventions, setInterventions] = useState<Intervention[]>([])
  const [summary, setSummary] = useState<StockSummary | null>(null)
  const [alerts, setAlerts] = useState<StockAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [partOpen, setPartOpen] = useState(false)
  const [movementOpen, setMovementOpen] = useState(false)
  const [working, setWorking] = useState(false)
  const [editing, setEditing] = useState<SparePart | null>(null)
  const [partForm, setPartForm] = useState({ code: "", name: "", category: "", quantity: "0", minimum_threshold: "0", unit_price: "0", supplier: "", active: true })
  const [movementForm, setMovementForm] = useState({ part_id: "", movement_type: "IN", quantity: "1", unit_cost: "0", intervention_id: "", reason: "" })

  const partMap = useMemo(() => new Map(parts.map((item) => [item.id, item])), [parts])
  const filteredParts = useMemo(() => { const query = search.trim().toLowerCase(); return parts.filter((item) => !query || [item.code, item.name, item.category, item.supplier].filter(Boolean).some((value) => String(value).toLowerCase().includes(query))) }, [parts, search])

  async function loadData() {
    setLoading(true); setError(null)
    try {
      const [partData, movementData, interventionData, summaryData, alertData] = await Promise.all([
        apiFetch<SparePart[]>("/spare-parts?limit=200"), apiFetch<StockMovement[]>("/stock-movements?limit=200"), apiFetch<Intervention[]>("/interventions?limit=200"), apiFetch<StockSummary>("/stock/summary"), apiFetch<StockAlertsResponse>("/stock/alerts?limit=500"),
      ])
      setParts(partData); setMovements(movementData); setInterventions(interventionData); setSummary(summaryData); setAlerts(alertData.items)
    } catch (caught) { setError(caught instanceof ApiError ? caught.detail : "Impossible de charger le stock.") } finally { setLoading(false) }
  }
  useEffect(() => { void loadData() }, [])

  function newPart() { setEditing(null); setPartForm({ code: "", name: "", category: "", quantity: "0", minimum_threshold: "0", unit_price: "0", supplier: "", active: true }); setPartOpen(true) }
  function editPart(item: SparePart) { setEditing(item); setPartForm({ code: item.code, name: item.name, category: item.category ?? "", quantity: String(item.quantity), minimum_threshold: String(item.minimum_threshold), unit_price: String(item.unit_price), supplier: item.supplier ?? "", active: item.active }); setPartOpen(true) }

  async function savePart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setWorking(true)
    try {
      if (editing) {
        const updated = await apiFetch<SparePart>(`/spare-parts/${editing.id}`, { method: "PATCH", body: JSON.stringify({ name: partForm.name, category: partForm.category || null, minimum_threshold: Number(partForm.minimum_threshold), unit_price: Number(partForm.unit_price), supplier: partForm.supplier || null, active: partForm.active }) })
        setParts((items) => items.map((item) => item.id === updated.id ? updated : item)); toast.success("Pièce mise à jour")
      } else {
        const created = await apiFetch<SparePart>("/spare-parts", { method: "POST", body: JSON.stringify({ code: partForm.code, name: partForm.name, category: partForm.category || null, quantity: Number(partForm.quantity), minimum_threshold: Number(partForm.minimum_threshold), unit_price: Number(partForm.unit_price), supplier: partForm.supplier || null }) })
        setParts((items) => [created, ...items]); toast.success("Pièce créée")
      }
      setPartOpen(false); await loadData()
    } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Enregistrement impossible.") } finally { setWorking(false) }
  }

  async function createMovement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setWorking(true)
    try {
      const created = await apiFetch<StockMovement>("/stock-movements", { method: "POST", body: JSON.stringify({ part_id: Number(movementForm.part_id), movement_type: movementForm.movement_type, quantity: Number(movementForm.quantity), unit_cost: Number(movementForm.unit_cost || 0), intervention_id: movementForm.intervention_id ? Number(movementForm.intervention_id) : null, reason: movementForm.reason || null }) })
      setMovements((items) => [created, ...items]); setMovementOpen(false); toast.success("Mouvement enregistré"); await loadData()
    } catch (caught) { toast.error(caught instanceof ApiError ? caught.detail : "Mouvement impossible.") } finally { setWorking(false) }
  }

  return <>
    <Header title="Stock et pièces détachées" description="Inventaire, mouvements, seuils, alertes, valorisation et traçabilité des pièces utilisées." searchValue={search} onSearchChange={setSearch} searchPlaceholder="Code, nom, catégorie ou fournisseur" actions={<>{canManage && <><Button className="h-9" onClick={newPart}><Plus className="mr-2 h-4 w-4" />Nouvelle pièce</Button><Dialog open={movementOpen} onOpenChange={setMovementOpen}><DialogTrigger asChild><Button variant="outline" className="h-9 bg-card"><PackageCheck className="mr-2 h-4 w-4" />Mouvement</Button></DialogTrigger><DialogContent><form onSubmit={createMovement}><DialogHeader><DialogTitle>Nouveau mouvement</DialogTitle><DialogDescription>Chaque mouvement met à jour la quantité physique et reste auditable.</DialogDescription></DialogHeader><div className="mt-5 space-y-4"><Field label="Pièce *"><Select value={movementForm.part_id} onValueChange={(value) => setMovementForm({ ...movementForm, part_id: value })}><SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{parts.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.code} · {item.name} · stock {item.quantity}</SelectItem>)}</SelectContent></Select></Field><div className="grid gap-4 sm:grid-cols-2"><Field label="Type"><Select value={movementForm.movement_type} onValueChange={(value) => setMovementForm({ ...movementForm, movement_type: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{movementTypes.map((value) => <SelectItem key={value} value={value}>{statusLabel(value)}</SelectItem>)}</SelectContent></Select></Field><Field label="Quantité"><Input type="number" min="1" value={movementForm.quantity} onChange={(event) => setMovementForm({ ...movementForm, quantity: event.target.value })} /></Field><Field label="Coût unitaire (MAD)"><Input type="number" min="0" step="0.01" value={movementForm.unit_cost} onChange={(event) => setMovementForm({ ...movementForm, unit_cost: event.target.value })} /></Field><Field label="Intervention"><Select value={movementForm.intervention_id || "NONE"} onValueChange={(value) => setMovementForm({ ...movementForm, intervention_id: value === "NONE" ? "" : value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="NONE">Aucune</SelectItem>{interventions.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.reference}</SelectItem>)}</SelectContent></Select></Field></div><Field label="Motif"><Textarea value={movementForm.reason} onChange={(event) => setMovementForm({ ...movementForm, reason: event.target.value })} /></Field></div><DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setMovementOpen(false)}>Annuler</Button><Button type="submit" disabled={working || !movementForm.part_id}>Enregistrer</Button></DialogFooter></form></DialogContent></Dialog></>}<Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button></>}/>
    <div className="mt-5 space-y-4">{error && <ErrorBanner message={error} />}<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"><Kpi label="Références" value={summary?.total_parts ?? 0} icon={Boxes} /><Kpi label="Quantité totale" value={summary?.total_quantity ?? 0} icon={PackageOpen} tone="blue" /><Kpi label="Stock faible" value={summary?.low_stock_parts ?? 0} icon={TrendingDown} tone="amber" /><Kpi label="Ruptures" value={summary?.out_of_stock_parts ?? 0} icon={AlertTriangle} tone="red" /><Card className="p-4 shadow-sm"><p className="text-xs text-muted-foreground">Valeur d’inventaire</p><p className="mt-2 text-2xl font-black">{formatMoney(summary?.inventory_value ?? 0)}</p></Card></div>{loading ? <LoadingState /> : <Tabs defaultValue="parts" className="space-y-4"><TabsList><TabsTrigger value="parts">Pièces</TabsTrigger><TabsTrigger value="alerts">Alertes ({alerts.length})</TabsTrigger><TabsTrigger value="movements">Mouvements</TabsTrigger></TabsList><TabsContent value="parts"><Card className="overflow-hidden shadow-sm">{filteredParts.length === 0 ? <div className="p-5"><EmptyState title="Aucune pièce" description="Ajoutez une première référence de stock." icon={PackageOpen} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Pièce</TableHead><TableHead>Catégorie</TableHead><TableHead>Quantité</TableHead><TableHead>Seuil</TableHead><TableHead>Prix</TableHead><TableHead>Fournisseur</TableHead><TableHead>État</TableHead><TableHead /></TableRow></TableHeader><TableBody>{filteredParts.map((item) => <TableRow key={item.id}><TableCell><p className="font-semibold">{item.code}</p><p className="text-xs text-muted-foreground">{item.name}</p></TableCell><TableCell>{item.category || "—"}</TableCell><TableCell><span className={item.quantity <= item.minimum_threshold ? "font-bold text-red-600" : "font-semibold"}>{item.quantity}</span></TableCell><TableCell>{item.minimum_threshold}</TableCell><TableCell>{formatMoney(item.unit_price)}</TableCell><TableCell>{item.supplier || "—"}</TableCell><TableCell><StatusBadge value={item.active ? "ACTIVE" : "INACTIVE"} /></TableCell><TableCell>{canManage && <Button size="icon" variant="ghost" onClick={() => editPart(item)}><Edit3 className="h-4 w-4" /></Button>}</TableCell></TableRow>)}</TableBody></Table></div>}</Card></TabsContent><TabsContent value="alerts"><Card className="overflow-hidden shadow-sm">{alerts.length === 0 ? <div className="p-5"><EmptyState title="Aucune alerte" description="Tous les stocks sont au-dessus des seuils." icon={PackageCheck} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Pièce</TableHead><TableHead>Stock</TableHead><TableHead>Seuil</TableHead><TableHead>Manque</TableHead><TableHead>Commande suggérée</TableHead><TableHead>Risque</TableHead></TableRow></TableHeader><TableBody>{alerts.map((item) => <TableRow key={item.part_id}><TableCell><p className="font-semibold">{item.code}</p><p className="text-xs text-muted-foreground">{item.name}</p></TableCell><TableCell>{item.quantity}</TableCell><TableCell>{item.minimum_threshold}</TableCell><TableCell className="text-red-600">{item.shortage}</TableCell><TableCell className="font-semibold">{item.suggested_order_quantity}</TableCell><TableCell><StatusBadge value={item.risk} /></TableCell></TableRow>)}</TableBody></Table></div>}</Card></TabsContent><TabsContent value="movements"><Card className="overflow-hidden shadow-sm"><div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Date</TableHead><TableHead>Pièce</TableHead><TableHead>Type</TableHead><TableHead>Quantité</TableHead><TableHead>Coût</TableHead><TableHead>Intervention</TableHead><TableHead>Motif</TableHead></TableRow></TableHeader><TableBody>{movements.map((item) => <TableRow key={item.id}><TableCell>{formatDateTime(item.created_at)}</TableCell><TableCell>{partMap.get(item.part_id)?.code ?? `#${item.part_id}`}</TableCell><TableCell><StatusBadge value={item.movement_type} /></TableCell><TableCell>{item.quantity}</TableCell><TableCell>{formatMoney(item.unit_cost)}</TableCell><TableCell>{item.intervention_id ? `#${item.intervention_id}` : "—"}</TableCell><TableCell className="max-w-72"><p className="line-clamp-2">{item.reason || "—"}</p></TableCell></TableRow>)}</TableBody></Table></div></Card></TabsContent></Tabs>}</div>

    <Dialog open={partOpen} onOpenChange={setPartOpen}><DialogContent><form onSubmit={savePart}><DialogHeader><DialogTitle>{editing ? "Modifier la pièce" : "Nouvelle pièce"}</DialogTitle><DialogDescription>Les quantités ultérieures sont gérées par les mouvements de stock.</DialogDescription></DialogHeader><div className="mt-5 grid gap-4 sm:grid-cols-2"><Field label="Code *"><Input value={partForm.code} disabled={Boolean(editing)} onChange={(event) => setPartForm({ ...partForm, code: event.target.value })} required /></Field><Field label="Nom *"><Input value={partForm.name} onChange={(event) => setPartForm({ ...partForm, name: event.target.value })} required /></Field><Field label="Catégorie"><Input value={partForm.category} onChange={(event) => setPartForm({ ...partForm, category: event.target.value })} /></Field>{!editing && <Field label="Quantité initiale"><Input type="number" min="0" value={partForm.quantity} onChange={(event) => setPartForm({ ...partForm, quantity: event.target.value })} /></Field>}<Field label="Seuil minimum"><Input type="number" min="0" value={partForm.minimum_threshold} onChange={(event) => setPartForm({ ...partForm, minimum_threshold: event.target.value })} /></Field><Field label="Prix unitaire"><Input type="number" min="0" step="0.01" value={partForm.unit_price} onChange={(event) => setPartForm({ ...partForm, unit_price: event.target.value })} /></Field><div className="sm:col-span-2"><Field label="Fournisseur"><Input value={partForm.supplier} onChange={(event) => setPartForm({ ...partForm, supplier: event.target.value })} /></Field></div>{editing && <Field label="État"><Select value={partForm.active ? "ACTIVE" : "INACTIVE"} onValueChange={(value) => setPartForm({ ...partForm, active: value === "ACTIVE" })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ACTIVE">Actif</SelectItem><SelectItem value="INACTIVE">Inactif</SelectItem></SelectContent></Select></Field>}</div><DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setPartOpen(false)}>Annuler</Button><Button type="submit" disabled={working}>{editing ? "Enregistrer" : "Créer"}</Button></DialogFooter></form></DialogContent></Dialog>
  </>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-2"><Label>{label}</Label>{children}</div> }
function Kpi({ label, value, icon: Icon, tone = "primary" }: { label: string; value: number; icon: typeof Boxes; tone?: "primary" | "blue" | "amber" | "red" }) { const colors = { primary: "bg-primary/10 text-primary", blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/30", amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/30", red: "bg-red-50 text-red-600 dark:bg-red-950/30" }; return <Card className="p-4 shadow-sm"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-3xl font-black">{value}</p></div><div className={`rounded-2xl p-3 ${colors[tone]}`}><Icon className="h-5 w-5" /></div></div></Card> }
