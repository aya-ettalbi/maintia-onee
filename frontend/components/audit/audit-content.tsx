"use client"

import { FileClock, RefreshCcw, ShieldCheck } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { SectionCard } from "@/components/common/section-card"
import { Header } from "@/components/dashboard/header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { apiFetch, ApiError } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import type { AuditLog } from "@/lib/types"

export function AuditContent() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      setLogs(await apiFetch<AuditLog[]>("/audit-logs?limit=500"))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Impossible de charger le journal d’audit.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadData() }, [])

  const filtered = useMemo(() => {
    const query = search.toLowerCase().trim()
    return logs.filter((item) => !query || `${item.action} ${item.entity_type} ${item.entity_id ?? ""}`.toLowerCase().includes(query))
  }, [logs, search])

  return (
    <>
      <Header title="Journal d’audit" description="Consultez les actions importantes enregistrées pour assurer la traçabilité de la plateforme." searchValue={search} onSearchChange={setSearch} searchPlaceholder="Action, entité ou identifiant" actions={<Button variant="outline" className="h-9 bg-transparent" onClick={() => void loadData()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button>} />
      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        <div className="rounded-2xl border border-primary/15 bg-primary/5 p-4"><div className="flex items-start gap-3"><div className="rounded-xl bg-primary/10 p-2.5 text-primary"><ShieldCheck className="h-5 w-5" /></div><div><p className="font-semibold">Traçabilité des opérations</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Les créations, modifications, changements de statut, mouvements de stock et recommandations sont journalisés par le backend.</p></div></div></div>
        <SectionCard title="Historique des actions" description={`${filtered.length} événement(s) affiché(s)`}>
          {loading ? <div className="p-4"><LoadingState /></div> : filtered.length === 0 ? <div className="p-4"><EmptyState title="Aucun événement" description="Les actions importantes apparaîtront ici." icon={FileClock} /></div> : <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Date</TableHead><TableHead>Action</TableHead><TableHead>Entité</TableHead><TableHead>Identifiant</TableHead><TableHead>Acteur</TableHead><TableHead>Détails</TableHead></TableRow></TableHeader><TableBody>{filtered.map((item) => <TableRow key={item.id}><TableCell className="whitespace-nowrap">{formatDateTime(item.occurred_at)}</TableCell><TableCell><span className="rounded-lg bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">{item.action}</span></TableCell><TableCell className="font-medium">{item.entity_type}</TableCell><TableCell>{item.entity_id ?? "—"}</TableCell><TableCell>{item.actor_id ? `Utilisateur #${item.actor_id}` : "Système"}</TableCell><TableCell className="max-w-80"><pre className="whitespace-pre-wrap break-words text-[10px] text-muted-foreground">{item.details ? JSON.stringify(item.details) : "—"}</pre></TableCell></TableRow>)}</TableBody></Table></div>}
        </SectionCard>
      </div>
    </>
  )
}
