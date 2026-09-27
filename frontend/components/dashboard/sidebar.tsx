"use client"

import {
  BarChart3,
  BellRing,
  Boxes,
  BrainCircuit,
  ClipboardList,
  Database,
  FileClock,
  FileText,
  Gauge,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  PackageOpen,
  Settings,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Users,
  Wrench,
} from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useAuth } from "@/components/auth/auth-provider"
import { cn } from "@/lib/utils"
import type { Role } from "@/lib/types"

const sections: Array<{
  label: string
  items: Array<{ icon: typeof LayoutDashboard; label: string; href: string; roles?: Role[] }>
}> = [
  {
    label: "Pilotage",
    items: [
      { icon: LayoutDashboard, label: "Vue générale", href: "/" },
      { icon: BarChart3, label: "Analytique", href: "/analytics" },
      { icon: FileText, label: "KPI et rapports", href: "/reports" },
      { icon: BellRing, label: "Notifications", href: "/notifications" },
    ],
  },
  {
    label: "Exploitation",
    items: [
      { icon: Database, label: "Historique ONEE", href: "/historique" },
      { icon: Boxes, label: "Parc informatique", href: "/equipments" },
      { icon: ClipboardList, label: "Demandes", href: "/requests" },
      { icon: Wrench, label: "Interventions", href: "/interventions" },
      { icon: PackageOpen, label: "Stock", href: "/stock" },
      { icon: Stethoscope, label: "Maintenance préventive", href: "/preventive" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { icon: BrainCircuit, label: "Assistant MaintIA", href: "/ai" },
      { icon: Gauge, label: "Prévisions de panne", href: "/forecasts" },
      { icon: Sparkles, label: "Recommandations", href: "/recommendations" },
    ],
  },
  {
    label: "Administration",
    items: [
      { icon: Users, label: "Utilisateurs", href: "/users", roles: ["ADMIN"] },
      { icon: Settings, label: "Référentiels", href: "/settings", roles: ["ADMIN", "MANAGER"] },
      { icon: FileClock, label: "Journal d’audit", href: "/audit", roles: ["ADMIN"] },
      { icon: HelpCircle, label: "Aide", href: "/help" },
    ],
  },
]

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`)
}

export function Sidebar({ embedded = false }: { embedded?: boolean } = {}) {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  return (
    <aside
      className={cn(
        "w-64 overflow-y-auto border-r border-border/80 bg-card/95 p-4 backdrop-blur-xl",
        embedded ? "h-full" : "fixed left-0 top-0 z-40 h-screen",
      )}
    >
      <Link href="/" className="mb-6 flex items-center gap-3 rounded-2xl p-1 transition-colors hover:bg-secondary/70">
        <div className="relative flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
          <Wrench className="h-5 w-5" />
          <span className="absolute -right-1 -top-1 rounded-full border-2 border-card bg-emerald-300 p-0.5 text-emerald-950">
            <Sparkles className="h-2.5 w-2.5" />
          </span>
        </div>
        <div className="leading-tight">
          <span className="block text-lg font-bold tracking-tight">MaintIA</span>
          <span className="block text-[9px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">ONEE · Branche Eau</span>
        </div>
      </Link>

      <div className="space-y-5">
        {sections.map((section) => {
          const visibleItems = section.items.filter((item) => !item.roles || item.roles.includes(user?.role as Role))
          if (visibleItems.length === 0) return null
          return (
            <div key={section.label}>
              <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{section.label}</p>
              <nav className="space-y-1">
                {visibleItems.map((item) => {
                  const active = isActive(pathname, item.href)
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "group flex items-center gap-2.5 rounded-xl px-3 py-2 text-[13px] font-medium transition-all",
                        active
                          ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                          : "text-muted-foreground hover:translate-x-0.5 hover:bg-secondary hover:text-foreground",
                      )}
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  )
                })}
              </nav>
            </div>
          )
        })}
      </div>

      <div className="mt-6 rounded-2xl border border-primary/15 bg-primary/[0.045] p-3">
        <div className="mb-2 flex items-center gap-2 text-primary">
          <ShieldCheck className="h-4 w-4" />
          <span className="text-xs font-semibold">Session sécurisée</span>
        </div>
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          {user?.first_name} {user?.last_name}<br />
          <span className="font-medium text-foreground">{user?.role}</span>
        </p>
      </div>

      <button
        type="button"
        onClick={logout}
        className="mt-3 flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-muted-foreground transition-all hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950/30"
      >
        <LogOut className="h-4 w-4" />
        Déconnexion
      </button>
    </aside>
  )
}
