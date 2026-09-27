"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import { apiFetch, clearAccessToken, getAccessToken, loginRequest, setAccessToken } from "@/lib/api"
import type { User } from "@/lib/types"

type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const token = getAccessToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const currentUser = await apiFetch<User>("/auth/me")
      setUser(currentUser)
    } catch {
      clearAccessToken()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshUser()
  }, [refreshUser])

  const login = useCallback(
    async (email: string, password: string) => {
      const token = await loginRequest(email, password)
      setAccessToken(token.access_token)
      const currentUser = await apiFetch<User>("/auth/me")
      setUser(currentUser)
      router.replace("/")
      router.refresh()
    },
    [router],
  )

  const logout = useCallback(() => {
    clearAccessToken()
    setUser(null)
    router.replace("/login")
    router.refresh()
  }, [router])

  const value = useMemo(
    () => ({ user, loading, login, logout, refreshUser }),
    [user, loading, login, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth doit être utilisé dans AuthProvider")
  return context
}
