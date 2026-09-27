import type { ReactNode } from "react"
import { Card } from "@/components/ui/card"

export function SectionCard({
  title,
  description,
  action,
  children,
  className = "",
}: {
  title: string
  description?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <Card className={`overflow-hidden border-border/80 bg-card shadow-sm ${className}`}>
      <div className="flex flex-col gap-3 border-b border-border/70 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-semibold text-foreground">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </Card>
  )
}
