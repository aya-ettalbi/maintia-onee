"use client"

import { Building2, MapPin, Pencil, Plus, RefreshCcw, Tags } from "lucide-react"
import { useEffect, useState, type FormEvent } from "react"
import { toast } from "sonner"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { Header } from "@/components/dashboard/header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { apiFetch, ApiError } from "@/lib/api"
import type { EquipmentCategory, OrganizationItem } from "@/lib/types"

type ReferenceType = "service" | "location" | "category"
type ReferenceDialog = { type: ReferenceType; item: OrganizationItem | null } | null

export function SettingsContent() {
  const [services, setServices] = useState<OrganizationItem[]>([])
  const [locations, setLocations] = useState<OrganizationItem[]>([])
  const [categories, setCategories] = useState<EquipmentCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialog, setDialog] = useState<ReferenceDialog>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ code: "", name: "", description: "" })

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [serviceData, locationData, categoryData] = await Promise.all([
        apiFetch<OrganizationItem[]>("/services?limit=200"),
        apiFetch<OrganizationItem[]>("/locations?limit=200"),
        apiFetch<EquipmentCategory[]>("/equipment-categories"),
      ])
      setServices(serviceData)
      setLocations(locationData)
      setCategories(categoryData)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les paramètres.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [])

  function openDialog(type: ReferenceType, item: OrganizationItem | null = null) {
    setForm({ code: item?.code ?? "", name: item?.name ?? "", description: item?.description ?? "" })
    setDialog({ type, item })
  }

  function endpointFor(type: ReferenceType, id?: number) {
    const base = type === "service" ? "/services" : type === "location" ? "/locations" : "/equipment-categories"
    return id ? `${base}/${id}` : base
  }

  function updateCollection(type: ReferenceType, item: OrganizationItem) {
    const updater = (current: OrganizationItem[]) => {
      const exists = current.some((value) => value.id === item.id)
      const next = exists ? current.map((value) => value.id === item.id ? item : value) : [...current, item]
      return next.sort((a, b) => a.name.localeCompare(b.name))
    }
    if (type === "service") setServices(updater)
    if (type === "location") setLocations(updater)
    if (type === "category") setCategories(updater)
  }

  async function saveItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!dialog) return
    setSubmitting(true)
    try {
      const item = await apiFetch<OrganizationItem>(endpointFor(dialog.type, dialog.item?.id), {
        method: dialog.item ? "PATCH" : "POST",
        body: JSON.stringify({
          code: form.code.trim(),
          name: form.name.trim(),
          description: form.description.trim() || null,
        }),
      })
      updateCollection(dialog.type, item)
      toast.success(dialog.item ? "Référentiel modifié" : "Référentiel créé")
      setDialog(null)
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Enregistrement impossible.")
    } finally {
      setSubmitting(false)
    }
  }

  const titles: Record<ReferenceType, [string, string]> = {
    service: ["service", "une entité ou un service de l’organisation"],
    location: ["localisation", "un site, bâtiment, étage ou espace d’affectation"],
    category: ["catégorie", "un type fonctionnel de matériel du parc"],
  }

  return (
    <>
      <Header title="Paramètres et référentiels" description="Administrez les services, localisations et catégories utilisés dans toute la plateforme." actions={<Button variant="outline" className="h-9 bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button>} />
      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        {loading ? <LoadingState /> : (
          <Tabs defaultValue="services" className="space-y-4">
            <TabsList className="grid w-full grid-cols-3 sm:w-auto"><TabsTrigger value="services">Services</TabsTrigger><TabsTrigger value="locations">Localisations</TabsTrigger><TabsTrigger value="categories">Catégories</TabsTrigger></TabsList>
            <TabsContent value="services"><ReferencePanel title="Services et entités" description="Structures auxquelles les utilisateurs et équipements sont rattachés." icon={Building2} items={services} onAdd={() => openDialog("service")} onEdit={(item) => openDialog("service", item)} /></TabsContent>
            <TabsContent value="locations"><ReferencePanel title="Localisations" description="Sites et emplacements physiques du parc informatique." icon={MapPin} items={locations} onAdd={() => openDialog("location")} onEdit={(item) => openDialog("location", item)} /></TabsContent>
            <TabsContent value="categories"><ReferencePanel title="Catégories d’équipement" description="Familles de matériels utilisées dans l’inventaire et les analyses." icon={Tags} items={categories} onAdd={() => openDialog("category")} onEdit={(item) => openDialog("category", item)} /></TabsContent>
          </Tabs>
        )}
      </div>

      <Dialog open={dialog !== null} onOpenChange={(open) => !open && setDialog(null)}>
        <DialogContent>
          <form onSubmit={saveItem}>
            <DialogHeader>
              <DialogTitle>{dialog ? `${dialog.item ? "Modifier" : "Créer"} ${titles[dialog.type][0]}` : "Référentiel"}</DialogTitle>
              <DialogDescription>{dialog ? `${dialog.item ? "Mettez à jour" : "Ajoutez"} ${titles[dialog.type][1]}.` : ""}</DialogDescription>
            </DialogHeader>
            <div className="mt-5 space-y-4">
              <div className="space-y-2"><Label>Code *</Label><Input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} placeholder="Ex. DTI" required /></div>
              <div className="space-y-2"><Label>Nom *</Label><Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></div>
              <div className="space-y-2"><Label>Description</Label><Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></div>
            </div>
            <DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={() => setDialog(null)}>Annuler</Button><Button type="submit" disabled={submitting}>{submitting ? "Enregistrement…" : "Enregistrer"}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

function ReferencePanel({ title, description, icon: Icon, items, onAdd, onEdit }: { title: string; description: string; icon: typeof Building2; items: OrganizationItem[]; onAdd: () => void; onEdit: (item: OrganizationItem) => void }) {
  return <Card className="overflow-hidden border-border/80 bg-card shadow-sm"><div className="flex flex-col gap-3 border-b border-border/70 p-5 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><div className="rounded-2xl bg-primary/10 p-3 text-primary"><Icon className="h-5 w-5" /></div><div><h2 className="font-semibold">{title}</h2><p className="text-xs text-muted-foreground">{description}</p></div></div><Button onClick={onAdd}><Plus className="mr-2 h-4 w-4" />Ajouter</Button></div>{items.length === 0 ? <div className="p-5"><EmptyState title="Aucun élément" description="Ajoutez le premier élément de ce référentiel." icon={Icon} /></div> : <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <div key={item.id} className="group rounded-2xl border border-border/80 p-4 transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"><div className="mb-3 flex items-center justify-between"><span className="rounded-lg bg-primary/10 px-2.5 py-1 text-xs font-bold text-primary">{item.code}</span><Button size="icon" variant="ghost" className="h-8 w-8 opacity-60 group-hover:opacity-100" onClick={() => onEdit(item)} aria-label={`Modifier ${item.name}`}><Pencil className="h-3.5 w-3.5" /></Button></div><p className="font-semibold">{item.name}</p><p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{item.description || "Aucune description."}</p></div>)}</div>}</Card>
}
