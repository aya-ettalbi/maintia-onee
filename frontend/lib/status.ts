const labels: Record<string, string> = {
  IN_SERVICE: "En service",
  IN_FAILURE: "En panne",
  IN_MAINTENANCE: "En maintenance",
  WAITING_PART: "En attente de pièce",
  OUT_OF_SERVICE: "Hors service",
  REFORMED: "Réformé",
  ARCHIVED: "Archivé",
  DRAFT: "Brouillon",
  SUBMITTED: "Soumise",
  VALIDATED: "Validée",
  REJECTED: "Rejetée",
  ASSIGNED: "Affectée",
  IN_PROGRESS: "En cours",
  RESOLVED: "Résolue",
  CLOSED: "Clôturée",
  CANCELLED: "Annulée",
  PLANNED: "Planifiée",
  WAITING: "En attente",
  DIAGNOSING: "Diagnostic",
  REPAIRING: "Réparation",
  WAITING_FOR_PART: "Attente de pièce",
  TESTING: "Test",
  COMPLETED: "Terminée",
  LOW: "Faible",
  MEDIUM: "Moyenne",
  HIGH: "Élevée",
  CRITICAL: "Critique",
  NEW: "Nouvelle",
  TO_REVIEW: "À analyser",
  ACCEPTED: "Acceptée",
  APPLIED: "Appliquée",
  EXPIRED: "Expirée",
  PREVENTIVE_MAINTENANCE: "Maintenance préventive",
  REPLACEMENT: "Remplacement",
  REFORM: "Réforme",
  STOCK_REPLENISHMENT: "Réapprovisionnement",
  PURCHASE_REVIEW: "Révision des achats",
  WORKLOAD_OPTIMIZATION: "Optimisation de charge",
  CORRECTIVE: "Corrective",
  PREVENTIVE: "Préventive",
  ADMIN: "Administrateur",
  MANAGER: "Responsable d’atelier",
  TECHNICIAN: "Technicien",
  STOCK_MANAGER: "Gestionnaire de stock",
  REQUESTER: "Demandeur",
  ACTIVE: "Actif",
  INACTIVE: "Inactif",
  IN: "Entrée",
  OUT: "Sortie",
  RETURN: "Retour",
  ADJUSTMENT_POSITIVE: "Ajustement +",
  ADJUSTMENT_NEGATIVE: "Ajustement −",
  INVENTORY: "Inventaire",
}

export function statusLabel(value?: string | null): string {
  if (!value) return "—"
  return labels[value] ?? value.replaceAll("_", " ").toLowerCase()
}

export function statusTone(value?: string | null): "green" | "red" | "amber" | "blue" | "slate" | "purple" {
  if (!value) return "slate"
  if (["IN_SERVICE", "COMPLETED", "CLOSED", "RESOLVED", "APPLIED", "ACTIVE", "IN", "RETURN"].includes(value)) return "green"
  if (["IN_FAILURE", "CRITICAL", "REJECTED", "CANCELLED", "OUT_OF_SERVICE", "EXPIRED", "ADJUSTMENT_NEGATIVE"].includes(value)) return "red"
  if (["WAITING", "WAITING_PART", "WAITING_FOR_PART", "MEDIUM", "HIGH", "TO_REVIEW", "SUBMITTED"].includes(value)) return "amber"
  if (["IN_PROGRESS", "DIAGNOSING", "REPAIRING", "TESTING", "ASSIGNED", "VALIDATED", "PLANNED"].includes(value)) return "blue"
  if (["PREVENTIVE", "PREVENTIVE_MAINTENANCE", "NEW"].includes(value)) return "purple"
  return "slate"
}
