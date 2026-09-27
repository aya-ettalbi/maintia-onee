import type { Role } from "@/lib/types"

export const roleLabels: Record<string, string> = {
  ADMIN: "Administrateur",
  MANAGER: "Responsable d’atelier",
  TECHNICIAN: "Technicien",
  STOCK_MANAGER: "Gestionnaire de stock",
  REQUESTER: "Demandeur",
}

export function hasRole(role: string | undefined, allowed: Role[]): boolean {
  return Boolean(role && allowed.includes(role as Role))
}

export const permissions = {
  admin: ["ADMIN"] as Role[],
  manager: ["ADMIN", "MANAGER"] as Role[],
  technician: ["ADMIN", "MANAGER", "TECHNICIAN"] as Role[],
  stock: ["ADMIN", "MANAGER", "STOCK_MANAGER"] as Role[],
  authenticated: ["ADMIN", "MANAGER", "TECHNICIAN", "STOCK_MANAGER", "REQUESTER"] as Role[],
}
