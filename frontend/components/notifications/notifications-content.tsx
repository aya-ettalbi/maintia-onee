"use client"

import { Bell, BellRing, CheckCheck, RefreshCcw } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { Header } from "@/components/dashboard/header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ApiError, apiFetch } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import type { Notification } from "@/lib/types"

export function NotificationsContent() {
  const [items, setItems] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState("ALL")

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      setItems(await apiFetch<Notification[]>("/notifications?limit=200"))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger les notifications.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [])

  const visible = useMemo(() => filter === "UNREAD" ? items.filter((item) => !item.read_at) : items, [filter, items])
  const unread = items.filter((item) => !item.read_at).length

  async function markOne(item: Notification) {
    if (item.read_at) return
    try {
      await apiFetch<{ message: string }>(`/notifications/${item.id}/read`, { method: "POST" })
      setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, read_at: new Date().toISOString() } : entry))
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Mise à jour impossible.")
    }
  }

  async function markAll() {
    try {
      await apiFetch<{ message: string }>("/notifications/read-all", { method: "POST" })
      const now = new Date().toISOString()
      setItems((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? now })))
      toast.success("Toutes les notifications sont lues")
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.detail : "Mise à jour impossible.")
    }
  }

  return (
    <>
      <Header title="Centre de notifications" description="Alertes de stock, maintenance préventive, prévisions de panne et événements métier." actions={<><Button onClick={() => void markAll()} disabled={unread === 0}><CheckCheck className="mr-2 h-4 w-4" />Tout marquer lu</Button><Button variant="outline" className="bg-card" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button></>} />
      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        <div className="grid gap-3 sm:grid-cols-3"><Card className="p-4"><p className="text-xs text-muted-foreground">Total</p><p className="mt-1 text-3xl font-black">{items.length}</p></Card><Card className="p-4"><p className="text-xs text-muted-foreground">Non lues</p><p className="mt-1 text-3xl font-black text-amber-600">{unread}</p></Card><Card className="p-4"><p className="text-xs text-muted-foreground">Lues</p><p className="mt-1 text-3xl font-black text-emerald-600">{items.length - unread}</p></Card></div>
        <Tabs value={filter} onValueChange={setFilter}><TabsList><TabsTrigger value="ALL">Toutes</TabsTrigger><TabsTrigger value="UNREAD">Non lues</TabsTrigger></TabsList></Tabs>
        {loading ? <LoadingState /> : visible.length === 0 ? <EmptyState title="Aucune notification" description="Les alertes générées par la plateforme apparaîtront ici." icon={BellRing} /> : <div className="grid gap-3">{visible.map((item) => <button key={item.id} type="button" onClick={() => void markOne(item)} className={`w-full rounded-2xl border p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md ${item.read_at ? "bg-card opacity-75" : "border-primary/20 bg-primary/[0.035]"}`}><div className="flex gap-3"><div className={`rounded-2xl p-3 ${item.read_at ? "bg-secondary text-muted-foreground" : "bg-primary/10 text-primary"}`}>{item.read_at ? <CheckCheck className="h-5 w-5" /> : <Bell className="h-5 w-5" />}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold">{item.title}</p><p className="text-[10px] text-muted-foreground">{formatDateTime(item.created_at)}</p></div><p className="mt-1 text-sm leading-relaxed text-muted-foreground">{item.message}</p></div></div></button>)}</div>}
      </div>
    </>
  )
}
