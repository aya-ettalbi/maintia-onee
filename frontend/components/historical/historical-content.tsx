"use client"

import {
  Archive,
  BarChart3,
  Boxes,
  ClipboardList,
  Clock3,
  Database,
  FileText,
  PackageOpen,
  RefreshCcw,
  Search,
  ShieldAlert,
  Wrench,
} from "lucide-react"
import Link from "next/link"
import { useEffect, useState, type FormEvent, type ReactNode } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { EmptyState } from "@/components/common/empty-state"
import { ErrorBanner } from "@/components/common/error-banner"
import { LoadingState } from "@/components/common/loading-state"
import { Header } from "@/components/dashboard/header"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { apiFetch, ApiError } from "@/lib/api"
import { formatDateTime, formatHours } from "@/lib/format"
import type {
  HistoricalAnalytics,
  HistoricalITSupply,
  HistoricalOfficeSupply,
  HistoricalPage,
  HistoricalRequest,
  HistoricalSecurityIncident,
  HistoricalSummary,
  HistoricalTask,
} from "@/lib/historical-types"


const PAGE_SIZE = 50
const chartColors = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
]


function messageFromError(caught: unknown, fallback: string): string {
  return caught instanceof ApiError ? caught.detail : fallback
}


function SourceBadge({ source = "Historique Excel" }: { source?: string }) {
  return (
    <span className="inline-flex whitespace-nowrap rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
      {source}
    </span>
  )
}


function RawStatus({ value }: { value: string | null }) {
  return (
    <span className="inline-flex max-w-48 rounded-full bg-secondary px-2.5 py-1 text-[10px] font-semibold text-foreground">
      {value || "Non renseigné"}
    </span>
  )
}


function PaginationBar({
  total,
  page,
  pageSize,
  onPageChange,
}: {
  total: number
  page: number
  pageSize: number
  onPageChange: (page: number) => void
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3">
      <p className="text-xs text-muted-foreground">
        {total.toLocaleString("fr-FR")} résultat(s)
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={page <= 1}
          onClick={() => onPageChange(Math.max(1, page - 1))}
        >
          Précédent
        </Button>
        <span className="px-2 text-xs font-semibold">
          Page {page} / {totalPages}
        </span>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={page >= totalPages}
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        >
          Suivant
        </Button>
      </div>
    </div>
  )
}


function SearchBar({
  value,
  onChange,
  onSubmit,
  placeholder,
}: {
  value: string
  onChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  placeholder: string
}) {
  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-2 sm:flex-row">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-10 pl-9"
          placeholder={placeholder}
        />
      </div>
      <Button type="submit" className="h-10">
        Rechercher
      </Button>
    </form>
  )
}


function SummaryCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = "primary",
}: {
  label: string
  value: number
  helper: string
  icon: typeof Database
  tone?: "primary" | "blue" | "amber" | "purple" | "green"
}) {
  const colors = {
    primary: "bg-primary/10 text-primary",
    blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/30",
    amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/30",
    purple: "bg-violet-50 text-violet-600 dark:bg-violet-950/30",
    green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30",
  }

  return (
    <Card className="border-border/80 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-bold">{value.toLocaleString("fr-FR")}</p>
          <p className="mt-1 text-[10px] text-muted-foreground">{helper}</p>
        </div>
        <div className={`rounded-xl p-3 ${colors[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </Card>
  )
}


export function HistoricalDashboardPanel() {
  const [summary, setSummary] = useState<HistoricalSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<HistoricalSummary>("/historical/summary")
      .then(setSummary)
      .catch((caught) => setError(messageFromError(caught, "Impossible de charger l’historique.")))
  }, [])

  if (error) return <ErrorBanner message={error} />
  if (!summary) return <LoadingState />

  return (
    <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/[0.06] to-card shadow-sm">
      <div className="flex flex-col gap-3 border-b border-border/70 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-primary p-2.5 text-primary-foreground">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-semibold">Historique ONEE intégré</h2>
            <p className="text-xs text-muted-foreground">
              Les anciennes données sont disponibles avec les nouvelles données opérationnelles.
            </p>
          </div>
        </div>
        <Button asChild variant="outline" size="sm" className="bg-card">
          <Link href="/historique">
            Explorer les 28 847 lignes
          </Link>
        </Button>
      </div>

      <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5">
        <MiniValue label="Demandes historiques" value={summary.requests_count} />
        <MiniValue label="Nouvelles demandes" value={summary.operational_requests_count} />
        <MiniValue label="Total demandes" value={summary.combined_requests_count} featured />
        <MiniValue label="Tâches historiques" value={summary.tasks_count} />
        <MiniValue label="Total interventions" value={summary.combined_interventions_count} featured />
      </div>
    </Card>
  )
}


function MiniValue({
  label,
  value,
  featured = false,
}: {
  label: string
  value: number
  featured?: boolean
}) {
  return (
    <div className={`rounded-xl border p-3 ${featured ? "border-primary/25 bg-primary text-primary-foreground" : "border-border bg-card"}`}>
      <p className={`text-[10px] ${featured ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold">{value.toLocaleString("fr-FR")}</p>
    </div>
  )
}


export function HistoricalOverviewContent() {
  const [summary, setSummary] = useState<HistoricalSummary | null>(null)
  const [recent, setRecent] = useState<HistoricalRequest[]>([])
  const [securityIncidents, setSecurityIncidents] = useState<HistoricalSecurityIncident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, recentData, securityData] = await Promise.all([
        apiFetch<HistoricalSummary>("/historical/summary"),
        apiFetch<HistoricalPage<HistoricalRequest>>("/historical/requests?limit=8"),
        apiFetch<HistoricalPage<HistoricalSecurityIncident>>("/historical/security-incidents?limit=10"),
      ])
      setSummary(summaryData)
      setRecent(recentData.items)
      setSecurityIncidents(securityData.items)
    } catch (caught) {
      setError(messageFromError(caught, "Impossible de charger les données historiques."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <>
      <Header
        title="Historique des données"
        description="Consultez les anciennes données ONEE et leur coexistence avec les nouvelles données créées dans MaintIA."
        actions={
          <Button variant="outline" className="h-9 bg-transparent" onClick={() => void load()}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Actualiser
          </Button>
        }
      />

      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}

        {loading || !summary ? (
          <LoadingState />
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              <SummaryCard label="Demandes historiques" value={summary.requests_count} helper="Ancien système Excel" icon={ClipboardList} />
              <SummaryCard label="Tâches historiques" value={summary.tasks_count} helper="Activités importées" icon={Wrench} tone="blue" />
              <SummaryCard label="Fournitures IT" value={summary.it_supplies_count} helper="Demandes historiques" icon={PackageOpen} tone="amber" />
              <SummaryCard label="Fournitures bureau" value={summary.office_supplies_count} helper="Demandes historiques" icon={Boxes} tone="purple" />
              <SummaryCard label="Incidents Himaya" value={summary.security_incidents_count} helper="Fiches historiques" icon={ShieldAlert} tone="green" />
              <SummaryCard label="Total importé" value={summary.total_historical_rows} helper="PostgreSQL" icon={Database} />
            </div>

            <Card className="border-border/80 p-4 shadow-sm">
              <div className="mb-4">
                <h2 className="font-semibold">Anciennes et nouvelles données</h2>
                <p className="text-xs text-muted-foreground">
                  Les données historiques restent consultables. Les nouvelles données continuent à être créées dans les modules opérationnels.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <CombinedValue label="Anciennes demandes" value={summary.requests_count} />
                <CombinedValue label="Nouvelles demandes" value={summary.operational_requests_count} />
                <CombinedValue label="Total demandes" value={summary.combined_requests_count} featured />
                <CombinedValue label="Total tâches et interventions" value={summary.combined_interventions_count} featured />
              </div>
            </Card>

            <div className="grid gap-4 lg:grid-cols-4">
              <ModuleLink href="/requests" title="Demandes" description="Historique et nouvelles demandes" icon={ClipboardList} />
              <ModuleLink href="/interventions" title="Interventions" description="Anciennes tâches et nouvelles interventions" icon={Wrench} />
              <ModuleLink href="/stock" title="Stock" description="Stock actuel et anciennes fournitures" icon={PackageOpen} />
              <ModuleLink href="/analytics" title="Analytique" description="Graphiques calculés sur l’historique" icon={BarChart3} />
            </div>

            <Card className="overflow-hidden border-border/80 shadow-sm">
              <div className="flex items-center justify-between border-b border-border p-4">
                <div>
                  <h2 className="font-semibold">Dernières demandes historiques</h2>
                  <p className="text-xs text-muted-foreground">Aperçu des données importées depuis Khadamate.</p>
                </div>
                <Button asChild size="sm" variant="outline">
                  <Link href="/requests">Tout afficher</Link>
                </Button>
              </div>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>N° demande</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Classification</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead>Source</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recent.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-semibold">{item.numero_demande}</TableCell>
                        <TableCell className="whitespace-nowrap">{formatDateTime(item.date_creation_demande)}</TableCell>
                        <TableCell className="max-w-md"><p className="line-clamp-2">{item.description_demande || "—"}</p></TableCell>
                        <TableCell>{item.classification || "—"}</TableCell>
                        <TableCell><RawStatus value={item.statut} /></TableCell>
                        <TableCell><SourceBadge /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </Card>

            <Card className="overflow-hidden border-border/80 shadow-sm">
              <div className="border-b border-border p-4">
                <h2 className="font-semibold">Incidents Himaya</h2>
                <p className="text-xs text-muted-foreground">Fiches de sécurité importées depuis l’historique.</p>
              </div>
              {securityIncidents.length === 0 ? (
                <div className="p-5"><EmptyState title="Aucun incident Himaya" description="Aucune fiche historique trouvée." icon={ShieldAlert} /></div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>N° fiche</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead>Incident</TableHead>
                        <TableHead>Cause</TableHead>
                        <TableHead>Impact</TableHead>
                        <TableHead>Groupe</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {securityIncidents.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-semibold">{item.numero_fiche || "—"}</TableCell>
                          <TableCell className="whitespace-nowrap">{formatDateTime(item.date_initiation)}</TableCell>
                          <TableCell><RawStatus value={item.statut} /></TableCell>
                          <TableCell className="min-w-64 max-w-md"><p className="line-clamp-3">{item.description_incident || "—"}</p></TableCell>
                          <TableCell className="min-w-52 max-w-sm"><p className="line-clamp-3">{item.cause_incident || "—"}</p></TableCell>
                          <TableCell className="min-w-52 max-w-sm"><p className="line-clamp-3">{item.impact_incident || "—"}</p></TableCell>
                          <TableCell>{item.groupe_traitement || "—"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </>
  )
}


function CombinedValue({ label, value, featured = false }: { label: string; value: number; featured?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${featured ? "border-primary/25 bg-primary/10" : "border-border bg-secondary/30"}`}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${featured ? "text-primary" : ""}`}>{value.toLocaleString("fr-FR")}</p>
    </div>
  )
}


function ModuleLink({
  href,
  title,
  description,
  icon: Icon,
}: {
  href: string
  title: string
  description: string
  icon: typeof ClipboardList
}) {
  return (
    <Link href={href}>
      <Card className="h-full border-border/80 p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg">
        <div className="mb-3 w-fit rounded-xl bg-primary/10 p-2.5 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <p className="font-semibold">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </Card>
    </Link>
  )
}


export function HistoricalRequestsContent() {
  const [data, setData] = useState<HistoricalPage<HistoricalRequest>>({
    total: 0,
    skip: 0,
    limit: PAGE_SIZE,
    items: [],
  })
  const [query, setQuery] = useState("")
  const [appliedQuery, setAppliedQuery] = useState("")
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * PAGE_SIZE),
        limit: String(PAGE_SIZE),
      })
      if (appliedQuery) params.set("q", appliedQuery)
      setData(await apiFetch<HistoricalPage<HistoricalRequest>>(`/historical/requests?${params}`))
    } catch (caught) {
      setError(messageFromError(caught, "Impossible de charger les demandes historiques."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [page, appliedQuery])

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPage(1)
    setAppliedQuery(query.trim())
  }

  return (
    <>
      <Header
        title="Demandes historiques"
        description="Consultez les demandes Khadamate importées. Les nouvelles demandes restent disponibles dans l’onglet Données actuelles."
        actions={<SourceBadge source={`${data.total.toLocaleString("fr-FR")} lignes importées`} />}
      />
      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        <Card className="border-border/80 p-4 shadow-sm">
          <SearchBar
            value={query}
            onChange={setQuery}
            onSubmit={search}
            placeholder="Numéro, description, demandeur, classification, cause ou solution"
          />
        </Card>

        <Card className="overflow-hidden border-border/80 shadow-sm">
          {loading ? (
            <div className="p-5"><LoadingState /></div>
          ) : data.items.length === 0 ? (
            <div className="p-5"><EmptyState title="Aucune demande historique" description="Modifiez la recherche." icon={Archive} /></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>N° demande</TableHead>
                    <TableHead>Création</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Classification</TableHead>
                    <TableHead>Demandeur</TableHead>
                    <TableHead>Intervenant</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead>Source</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="whitespace-nowrap font-semibold">{item.numero_demande}</TableCell>
                      <TableCell className="whitespace-nowrap">{formatDateTime(item.date_creation_demande)}</TableCell>
                      <TableCell className="min-w-72 max-w-lg">
                        <p className="line-clamp-3 text-sm">{item.description_demande || "—"}</p>
                        {(item.cause || item.solution) && (
                          <div className="mt-2 space-y-1 text-[10px] text-muted-foreground">
                            {item.cause && <p><strong>Cause :</strong> {item.cause}</p>}
                            {item.solution && <p><strong>Solution :</strong> {item.solution}</p>}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>{item.classification || item.detail_classification || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{item.demandeur || [item.prenom_demandeur, item.nom_demandeur].filter(Boolean).join(" ") || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{item.dernier_intervenant || "—"}</TableCell>
                      <TableCell><RawStatus value={item.statut} /></TableCell>
                      <TableCell><SourceBadge /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <PaginationBar total={data.total} page={page} pageSize={PAGE_SIZE} onPageChange={setPage} />
        </Card>
      </div>
    </>
  )
}


export function HistoricalTasksContent() {
  const [data, setData] = useState<HistoricalPage<HistoricalTask>>({
    total: 0,
    skip: 0,
    limit: PAGE_SIZE,
    items: [],
  })
  const [query, setQuery] = useState("")
  const [appliedQuery, setAppliedQuery] = useState("")
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * PAGE_SIZE),
        limit: String(PAGE_SIZE),
      })
      if (appliedQuery) params.set("q", appliedQuery)
      setData(await apiFetch<HistoricalPage<HistoricalTask>>(`/historical/tasks?${params}`))
    } catch (caught) {
      setError(messageFromError(caught, "Impossible de charger les tâches historiques."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [page, appliedQuery])

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPage(1)
    setAppliedQuery(query.trim())
  }

  return (
    <>
      <Header
        title="Tâches historiques"
        description="Consultez les tâches Khadamate importées. Les nouvelles interventions restent disponibles dans l’onglet Données actuelles."
        actions={<SourceBadge source={`${data.total.toLocaleString("fr-FR")} lignes importées`} />}
      />
      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        <Card className="border-border/80 p-4 shadow-sm">
          <SearchBar
            value={query}
            onChange={setQuery}
            onSubmit={search}
            placeholder="N° tâche, n° demande, description, intervenant ou classification"
          />
        </Card>

        <Card className="overflow-hidden border-border/80 shadow-sm">
          {loading ? (
            <div className="p-5"><LoadingState /></div>
          ) : data.items.length === 0 ? (
            <div className="p-5"><EmptyState title="Aucune tâche historique" description="Modifiez la recherche." icon={Archive} /></div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>N° tâche</TableHead>
                    <TableHead>N° demande</TableHead>
                    <TableHead>Création</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Classification</TableHead>
                    <TableHead>Intervenant</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead>Source</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="whitespace-nowrap font-semibold">{item.numero_tache}</TableCell>
                      <TableCell className="whitespace-nowrap">{item.numero_demande || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{formatDateTime(item.date_creation_tache)}</TableCell>
                      <TableCell className="min-w-72 max-w-lg"><p className="line-clamp-3">{item.description_tache || item.detail_demande || "—"}</p></TableCell>
                      <TableCell>{item.classification_tache || item.classification_demande || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">{item.intervenant || item.groupe_intervenant || "—"}</TableCell>
                      <TableCell><RawStatus value={item.statut_tache} /></TableCell>
                      <TableCell><SourceBadge /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <PaginationBar total={data.total} page={page} pageSize={PAGE_SIZE} onPageChange={setPage} />
        </Card>
      </div>
    </>
  )
}


export function HistoricalSuppliesContent() {
  return (
    <>
      <Header
        title="Historique des fournitures"
        description="Consultez les anciennes demandes de fournitures sans les confondre avec le stock physique actuel."
      />
      <div className="mt-5">
        <Tabs defaultValue="it">
          <TabsList>
            <TabsTrigger value="it">Fournitures informatiques</TabsTrigger>
            <TabsTrigger value="office">Fournitures de bureau</TabsTrigger>
          </TabsList>
          <TabsContent value="it" className="mt-4">
            <HistoricalITSuppliesTable />
          </TabsContent>
          <TabsContent value="office" className="mt-4">
            <HistoricalOfficeSuppliesTable />
          </TabsContent>
        </Tabs>
      </div>
    </>
  )
}


function HistoricalITSuppliesTable() {
  const [data, setData] = useState<HistoricalPage<HistoricalITSupply>>({ total: 0, skip: 0, limit: PAGE_SIZE, items: [] })
  const [query, setQuery] = useState("")
  const [appliedQuery, setAppliedQuery] = useState("")
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams({ skip: String((page - 1) * PAGE_SIZE), limit: String(PAGE_SIZE) })
    if (appliedQuery) params.set("q", appliedQuery)
    setLoading(true)
    apiFetch<HistoricalPage<HistoricalITSupply>>(`/historical/it-supplies?${params}`)
      .then(setData)
      .catch((caught) => setError(messageFromError(caught, "Impossible de charger les fournitures IT.")))
      .finally(() => setLoading(false))
  }, [page, appliedQuery])

  return (
    <Card className="overflow-hidden border-border/80 shadow-sm">
      <div className="border-b border-border p-4">
        <SearchBar
          value={query}
          onChange={setQuery}
          onSubmit={(event) => { event.preventDefault(); setPage(1); setAppliedQuery(query.trim()) }}
          placeholder="Numéro, initiateur, motif, article ou récepteur"
        />
      </div>
      {error && <div className="p-4"><ErrorBanner message={error} /></div>}
      {loading ? <div className="p-5"><LoadingState /></div> : data.items.length === 0 ? <div className="p-5"><EmptyState title="Aucune fourniture IT" description="Aucune ligne trouvée." icon={PackageOpen} /></div> : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>N° demande</TableHead><TableHead>Initiation</TableHead><TableHead>Étape</TableHead><TableHead>Direction</TableHead><TableHead>Motif</TableHead><TableHead>Articles</TableHead><TableHead>Récepteur</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-semibold">{item.numero_demande || "—"}</TableCell>
                  <TableCell className="whitespace-nowrap">{formatDateTime(item.date_initiation)}</TableCell>
                  <TableCell>{item.etape_en_cours || "—"}</TableCell>
                  <TableCell>{item.direction || "—"}</TableCell>
                  <TableCell className="min-w-64 max-w-md"><p className="line-clamp-3">{item.motif_demande || "—"}</p></TableCell>
                  <TableCell className="min-w-64 max-w-md"><p className="line-clamp-3">{item.articles || "—"}</p></TableCell>
                  <TableCell>{item.nom_recepteur || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <PaginationBar total={data.total} page={page} pageSize={PAGE_SIZE} onPageChange={setPage} />
    </Card>
  )
}


function HistoricalOfficeSuppliesTable() {
  const [data, setData] = useState<HistoricalPage<HistoricalOfficeSupply>>({ total: 0, skip: 0, limit: PAGE_SIZE, items: [] })
  const [query, setQuery] = useState("")
  const [appliedQuery, setAppliedQuery] = useState("")
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams({ skip: String((page - 1) * PAGE_SIZE), limit: String(PAGE_SIZE) })
    if (appliedQuery) params.set("q", appliedQuery)
    setLoading(true)
    apiFetch<HistoricalPage<HistoricalOfficeSupply>>(`/historical/office-supplies?${params}`)
      .then(setData)
      .catch((caught) => setError(messageFromError(caught, "Impossible de charger les fournitures de bureau.")))
      .finally(() => setLoading(false))
  }, [page, appliedQuery])

  return (
    <Card className="overflow-hidden border-border/80 shadow-sm">
      <div className="border-b border-border p-4">
        <SearchBar
          value={query}
          onChange={setQuery}
          onSubmit={(event) => { event.preventDefault(); setPage(1); setAppliedQuery(query.trim()) }}
          placeholder="Référence, expéditeur ou direction"
        />
      </div>
      {error && <div className="p-4"><ErrorBanner message={error} /></div>}
      {loading ? <div className="p-5"><LoadingState /></div> : data.items.length === 0 ? <div className="p-5"><EmptyState title="Aucune fourniture de bureau" description="Aucune ligne trouvée." icon={Boxes} /></div> : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Référence</TableHead><TableHead>Référence consolidée</TableHead><TableHead>Initiation</TableHead><TableHead>Traitement</TableHead><TableHead>Expéditeur</TableHead><TableHead>Étape</TableHead><TableHead>Direction</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-semibold">{item.reference || "—"}</TableCell>
                  <TableCell>{item.reference_consolidee || "—"}</TableCell>
                  <TableCell className="whitespace-nowrap">{formatDateTime(item.date_initiation)}</TableCell>
                  <TableCell className="whitespace-nowrap">{formatDateTime(item.date_traitement)}</TableCell>
                  <TableCell>{item.expediteur || "—"}</TableCell>
                  <TableCell>{item.etape_en_cours || "—"}</TableCell>
                  <TableCell>{item.direction || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <PaginationBar total={data.total} page={page} pageSize={PAGE_SIZE} onPageChange={setPage} />
    </Card>
  )
}


export function HistoricalAnalyticsContent() {
  const [analytics, setAnalytics] = useState<HistoricalAnalytics | null>(null)
  const [summary, setSummary] = useState<HistoricalSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [analyticsData, summaryData] = await Promise.all([
        apiFetch<HistoricalAnalytics>("/historical/analytics"),
        apiFetch<HistoricalSummary>("/historical/summary"),
      ])
      setAnalytics(analyticsData)
      setSummary(summaryData)
    } catch (caught) {
      setError(messageFromError(caught, "Impossible de charger l’analyse historique."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <>
      <Header
        title="Analytique historique"
        description="Analysez les 13 399 demandes et les 15 331 tâches importées depuis les données ONEE."
        actions={<Button variant="outline" className="h-9 bg-transparent" onClick={() => void load()}><RefreshCcw className="mr-2 h-4 w-4" />Actualiser</Button>}
      />

      <div className="mt-5 space-y-4">
        {error && <ErrorBanner message={error} />}
        {loading || !analytics || !summary ? <LoadingState /> : (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <SummaryCard label="Demandes analysées" value={summary.requests_count} helper="Historique Khadamate" icon={ClipboardList} />
              <SummaryCard label="Tâches analysées" value={summary.tasks_count} helper="Historique des tâches" icon={Wrench} tone="blue" />
              <SummaryCard label="Solutions disponibles" value={analytics.requests_with_solution} helper="Utilisables par l’assistant IA" icon={FileText} tone="green" />
              <Card className="border-border/80 p-4 shadow-sm">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Délai moyen historique</p>
                    <p className="mt-2 text-2xl font-bold">{formatHours(analytics.average_resolution_hours)}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">Lorsque les deux dates sont disponibles</p>
                  </div>
                  <div className="rounded-xl bg-amber-50 p-3 text-amber-600"><Clock3 className="h-5 w-5" /></div>
                </div>
              </Card>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <HistoricalChart title="Évolution mensuelle des demandes" description="Nombre de demandes créées par mois">
                <ResponsiveContainer width="100%" height={310}>
                  <LineChart data={analytics.monthly_requests}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.25} />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} angle={-25} textAnchor="end" height={65} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="var(--color-chart-1)" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </HistoricalChart>

              <HistoricalChart title="Statuts des demandes" description="Répartition des demandes historiques">
                <ResponsiveContainer width="100%" height={310}>
                  <PieChart>
                    <Pie data={analytics.request_statuses} dataKey="value" nameKey="name" innerRadius={65} outerRadius={105} paddingAngle={3}>
                      {analytics.request_statuses.map((item, index) => <Cell key={`${item.name}-${index}`} fill={chartColors[index % chartColors.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </HistoricalChart>

              <HistoricalChart title="Classifications les plus fréquentes" description="Top des catégories de demandes">
                <ResponsiveContainer width="100%" height={360}>
                  <BarChart data={analytics.request_classifications} layout="vertical" margin={{ left: 25, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.25} />
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 9 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="var(--color-chart-2)" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </HistoricalChart>

              <HistoricalChart title="Intervenants les plus sollicités" description="Top des intervenants dans les tâches historiques">
                <ResponsiveContainer width="100%" height={360}>
                  <BarChart data={analytics.top_technicians} layout="vertical" margin={{ left: 25, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.25} />
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 9 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="var(--color-chart-3)" radius={[0, 8, 8, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </HistoricalChart>
            </div>
          </>
        )}
      </div>
    </>
  )
}


function HistoricalChart({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <Card className="overflow-hidden border-border/80 shadow-sm">
      <div className="border-b border-border p-5">
        <h2 className="font-semibold">{title}</h2>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <div className="p-4">{children}</div>
    </Card>
  )
}
