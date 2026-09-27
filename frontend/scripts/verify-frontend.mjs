import { existsSync, readFileSync } from "node:fs"
import { join } from "node:path"

const root = process.cwd()
const requiredPages = [
  "app/page.tsx",
  "app/login/page.tsx",
  "app/equipments/page.tsx",
  "app/requests/page.tsx",
  "app/interventions/page.tsx",
  "app/stock/page.tsx",
  "app/preventive/page.tsx",
  "app/reports/page.tsx",
  "app/ai/page.tsx",
  "app/forecasts/page.tsx",
  "app/recommendations/page.tsx",
  "app/notifications/page.tsx",
  "app/users/page.tsx",
  "app/settings/page.tsx",
  "app/audit/page.tsx",
]

const requiredApiMarkers = [
  "/auth/login",
  "/dashboard/summary",
  "/equipments",
  "/maintenance-requests",
  "/interventions",
  "/stock/summary",
  "/preventive-maintenance/plans",
  "/kpi/maintenance",
  "/reports/monthly",
  "/chat",
  "/ai/triage",
  "/ai/failure-forecasts/summary",
  "/recommendations",
  "/notifications/unread-count",
]

const missingPages = requiredPages.filter((path) => !existsSync(join(root, path)))
const sourceFiles = [
  "lib/api.ts",
  "components/dashboard/dashboard-content.tsx",
  "components/equipments/equipments-content.tsx",
  "components/requests/requests-content.tsx",
  "components/interventions/interventions-content.tsx",
  "components/stock/stock-content.tsx",
  "components/preventive/preventive-content.tsx",
  "components/reports/reports-content.tsx",
  "components/ai/ai-content.tsx",
  "components/forecasts/forecasts-content.tsx",
  "components/recommendations/recommendations-content.tsx",
  "components/dashboard/header.tsx",
].map((path) => readFileSync(join(root, path), "utf8")).join("\n")
const missingMarkers = requiredApiMarkers.filter((value) => !sourceFiles.includes(value))

console.log(`Pages vérifiées : ${requiredPages.length - missingPages.length}/${requiredPages.length}`)
console.log(`Groupes API vérifiés : ${requiredApiMarkers.length - missingMarkers.length}/${requiredApiMarkers.length}`)

if (missingPages.length || missingMarkers.length) {
  if (missingPages.length) console.error("Pages manquantes :", missingPages)
  if (missingMarkers.length) console.error("Connexions API manquantes :", missingMarkers)
  process.exit(1)
}

console.log("Frontend MaintIA : structure et connexions principales OK")
