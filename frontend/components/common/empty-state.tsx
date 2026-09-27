import type { LucideIcon } from "lucide-react"
import { Inbox } from "lucide-react"

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
}: {
  title: string
  description: string
  icon?: LucideIcon
}) {
  return (
    <div className="min-h-52 flex items-center justify-center rounded-2xl border border-dashed bg-card p-8 text-center">
      <div className="max-w-sm">
        <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <h3 className="font-semibold text-foreground">{title}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}
