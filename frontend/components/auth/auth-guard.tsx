"use client"

import { useEffect, type ReactNode } from "react"
import { usePathname, useRouter } from "next/navigation"
import { LoaderCircle } from "lucide-react"
import { useAuth } from "@/components/auth/auth-provider"

export function AuthGuard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!loading && !user && pathname !== "/login") {
      router.replace("/login")
    }
  }, [loading, pathname, router, user])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm">Chargement de la plateforme…</p>
        </div>
      </div>
    )
  }

  if (!user) return null
  return <>{children}</>
}
