"use client"

import type { ReactNode } from "react"
import { AuthGuard } from "@/components/auth/auth-guard"
import { Sidebar } from "@/components/dashboard/sidebar"

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <div className="maintia-shell flex min-h-screen bg-background">
        <div className="hidden lg:block">
          <Sidebar />
        </div>
        <main className="relative flex-1 p-3 md:p-4 lg:ml-64 lg:p-5"><div className="relative z-10 mx-auto w-full max-w-[1800px]">{children}</div></main>
      </div>
    </AuthGuard>
  )
}
