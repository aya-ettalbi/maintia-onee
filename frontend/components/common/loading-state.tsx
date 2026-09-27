import { LoaderCircle } from "lucide-react"

export function LoadingState({ label = "Chargement des données…" }: { label?: string }) {
  return (
    <div className="min-h-52 flex items-center justify-center rounded-2xl border border-dashed bg-card">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <LoaderCircle className="h-7 w-7 animate-spin text-primary" />
        <p className="text-sm">{label}</p>
      </div>
    </div>
  )
}
