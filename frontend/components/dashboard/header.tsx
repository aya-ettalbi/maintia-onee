"use client"

import { Bell, CheckCheck, Cloud, CloudOff, Moon, Search, Sun } from "lucide-react"
import Link from "next/link"
import type { ReactNode } from "react"
import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { useAuth } from "@/components/auth/auth-provider"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { apiFetch, checkBackend } from "@/lib/api"
import { formatDateTime, initials } from "@/lib/format"
import { roleLabels } from "@/lib/permissions"
import type { Notification } from "@/lib/types"
import { MobileNav } from "./mobile-nav"

interface HeaderProps {
  title: string
  description: string
  actions?: ReactNode
  searchValue?: string
  onSearchChange?: (value: string) => void
  searchPlaceholder?: string
}

export function Header({ title, description, actions, searchValue, onSearchChange, searchPlaceholder = "Rechercher dans la plateforme" }: HeaderProps) {
  const { user } = useAuth()
  const { resolvedTheme, setTheme } = useTheme()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [online, setOnline] = useState(true)

  async function refreshHeader() {
    const [health, notificationsResult, countResult] = await Promise.allSettled([
      checkBackend(),
      apiFetch<Notification[]>("/notifications?limit=8"),
      apiFetch<{ unread_count: number }>("/notifications/unread-count"),
    ])
    setOnline(health.status === "fulfilled" && health.value)
    if (notificationsResult.status === "fulfilled") setNotifications(notificationsResult.value)
    if (countResult.status === "fulfilled") setUnreadCount(countResult.value.unread_count)
  }

  useEffect(() => {
    void refreshHeader()
    const timer = window.setInterval(() => void refreshHeader(), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  async function markAsRead(item: Notification) {
    if (item.read_at) return
    try {
      await apiFetch<{ message: string }>(`/notifications/${item.id}/read`, { method: "POST" })
      setNotifications((current) => current.map((notification) => notification.id === item.id ? { ...notification, read_at: new Date().toISOString() } : notification))
      setUnreadCount((value) => Math.max(0, value - 1))
    } catch {
      // La notification ne bloque pas l’interface.
    }
  }

  async function markAll() {
    try {
      await apiFetch<{ message: string }>("/notifications/read-all", { method: "POST" })
      const now = new Date().toISOString()
      setNotifications((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? now })))
      setUnreadCount(0)
    } catch {
      // La notification ne bloque pas l’interface.
    }
  }

  return (
    <header className="space-y-4 animate-slide-in-up">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <MobileNav />
          {onSearchChange && (
            <div className="relative max-w-md flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={searchValue} onChange={(event) => onSearchChange(event.target.value)} placeholder={searchPlaceholder} className="h-9 bg-card pl-9" />
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className={online ? "hidden gap-1.5 border-emerald-200 bg-emerald-50 text-emerald-700 sm:flex dark:border-emerald-900 dark:bg-emerald-950/20 dark:text-emerald-300" : "hidden gap-1.5 border-red-200 bg-red-50 text-red-700 sm:flex dark:border-red-900 dark:bg-red-950/20 dark:text-red-300"}>
            {online ? <Cloud className="h-3.5 w-3.5" /> : <CloudOff className="h-3.5 w-3.5" />}
            {online ? "Backend connecté" : "Backend hors ligne"}
          </Badge>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9"
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            aria-label="Changer le thème"
          >
            {resolvedTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" className="relative h-9 w-9"><Bell className="h-4 w-4" />{unreadCount > 0 && <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[9px] font-bold text-white">{unreadCount > 99 ? "99+" : unreadCount}</span>}</Button></DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 rounded-xl p-2">
              <DropdownMenuLabel className="flex items-center justify-between">Notifications<Button type="button" variant="ghost" size="sm" disabled={unreadCount === 0} onClick={() => void markAll()}><CheckCheck className="mr-1 h-3.5 w-3.5" />Tout lire</Button></DropdownMenuLabel>
              <DropdownMenuSeparator />
              <div className="max-h-80 space-y-1 overflow-y-auto">{notifications.length === 0 ? <div className="p-5 text-center text-sm text-muted-foreground">Aucune notification.</div> : notifications.map((item) => <button type="button" key={item.id} onClick={() => void markAsRead(item)} className={`w-full rounded-lg p-3 text-left transition-colors hover:bg-secondary ${item.read_at ? "opacity-65" : "bg-primary/5"}`}><p className="text-xs font-semibold">{item.title}</p><p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{item.message}</p><p className="mt-1.5 text-[10px] text-muted-foreground">{formatDateTime(item.created_at)}</p></button>)}</div>
              <DropdownMenuSeparator /><Button asChild variant="ghost" className="w-full"><Link href="/notifications">Ouvrir le centre de notifications</Link></Button>
            </DropdownMenuContent>
          </DropdownMenu>

          <div className="flex items-center gap-2 border-l pl-2">
            <Avatar className="h-8 w-8 ring-2 ring-primary/20"><AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">{initials(user?.first_name, user?.last_name)}</AvatarFallback></Avatar>
            <div className="hidden text-xs sm:block"><p className="font-semibold">{user?.first_name} {user?.last_name}</p><p className="text-[10px] text-muted-foreground">{roleLabels[user?.role ?? ""] ?? user?.role}</p></div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div><h1 className="text-2xl font-black tracking-tight md:text-3xl">{title}</h1><p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted-foreground">{description}</p></div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </header>
  )
}
