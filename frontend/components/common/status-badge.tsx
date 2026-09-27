import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { statusLabel, statusTone } from "@/lib/status"

const tones = {
  green: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300",
  red: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300",
  amber: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300",
  blue: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300",
  purple: "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-300",
  slate: "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300",
}

export function StatusBadge({ value, className }: { value?: string | null; className?: string }) {
  const tone = statusTone(value)
  return (
    <Badge variant="outline" className={cn("rounded-full px-2.5 py-1 font-medium", tones[tone], className)}>
      {statusLabel(value)}
    </Badge>
  )
}
