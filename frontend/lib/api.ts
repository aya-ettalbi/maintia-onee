const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1"
const TOKEN_KEY = "maintenance_onee_access_token"
const DEFAULT_TIMEOUT_MS = 45_000

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setAccessToken(token: string): void {
  if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_KEY)
}

export function buildQuery(values: Record<string, string | number | boolean | null | undefined>): string {
  const params = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") params.set(key, String(value))
  })
  const query = params.toString()
  return query ? `?${query}` : ""
}

function extractError(payload: unknown): string {
  if (typeof payload === "string" && payload.trim()) return payload
  if (payload && typeof payload === "object") {
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === "string") return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) return String((item as { msg: unknown }).msg)
          return String(item)
        })
        .join(" · ")
    }
  }
  return "Une erreur inattendue est survenue."
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { auth?: boolean; timeoutMs?: number } = {},
): Promise<T> {
  const { auth = true, timeoutMs = DEFAULT_TIMEOUT_MS, headers, signal, ...requestOptions } = options
  const finalHeaders = new Headers(headers)

  if (!finalHeaders.has("Content-Type") && requestOptions.body && !(requestOptions.body instanceof FormData)) {
    finalHeaders.set("Content-Type", "application/json")
  }

  if (auth) {
    const token = getAccessToken()
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`)
  }

  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  const abort = () => controller.abort()
  signal?.addEventListener("abort", abort)

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...requestOptions,
      headers: finalHeaders,
      cache: "no-store",
      signal: controller.signal,
    })

    if (response.status === 401 && auth) {
      clearAccessToken()
      if (typeof window !== "undefined" && window.location.pathname !== "/login") window.location.href = "/login"
    }

    if (!response.ok) {
      let payload: unknown = null
      try {
        payload = await response.json()
      } catch {
        payload = await response.text()
      }
      throw new ApiError(response.status, extractError(payload))
    }

    if (response.status === 204) return undefined as T
    const contentType = response.headers.get("content-type") ?? ""
    if (!contentType.includes("application/json")) return (await response.text()) as T
    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(408, "Le backend a mis trop de temps à répondre.")
    }
    throw new ApiError(0, "Impossible de joindre le backend FastAPI.")
  } finally {
    window.clearTimeout(timeout)
    signal?.removeEventListener("abort", abort)
  }
}

export async function loginRequest(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
  const body = new URLSearchParams()
  body.set("username", email)
  body.set("password", password)

  return apiFetch<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    auth: false,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  })
}

export async function checkBackend(): Promise<boolean> {
  try {
    await apiFetch<Record<string, string>>("/system/health", { auth: false, timeoutMs: 5000 })
    return true
  } catch {
    return false
  }
}

export { API_URL }
