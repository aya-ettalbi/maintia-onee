import { StockWorkspace } from "@/components/historical/workspaces"
import { AppShell } from "@/components/layout/app-shell"

export default function StockPage() {
  return (
    <AppShell>
      <StockWorkspace />
    </AppShell>
  )
}
