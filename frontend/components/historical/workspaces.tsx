"use client"

import { Archive, Layers3, PlusCircle } from "lucide-react"
import { useState } from "react"
import { AnalyticsContent } from "@/components/analytics/analytics-content"
import { InterventionsContent } from "@/components/interventions/interventions-content"
import { RequestsContent } from "@/components/requests/requests-content"
import { StockContent } from "@/components/stock/stock-content"
import {
  HistoricalAnalyticsContent,
  HistoricalRequestsContent,
  HistoricalSuppliesContent,
  HistoricalTasksContent,
} from "@/components/historical/historical-content"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"


type Mode = "history" | "current"


function ModeBar({
  mode,
  onModeChange,
  historyLabel,
  currentLabel,
  description,
}: {
  mode: Mode
  onModeChange: (mode: Mode) => void
  historyLabel: string
  currentLabel: string
  description: string
}) {
  return (
    <Card className="mb-4 border-primary/15 bg-primary/[0.035] p-3 shadow-sm">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-primary/10 p-2 text-primary">
            <Layers3 className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold">Mode d’affichage</p>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            type="button"
            variant={mode === "history" ? "default" : "outline"}
            className={mode === "history" ? "" : "bg-card"}
            onClick={() => onModeChange("history")}
          >
            <Archive className="mr-2 h-4 w-4" />
            {historyLabel}
          </Button>
          <Button
            type="button"
            variant={mode === "current" ? "default" : "outline"}
            className={mode === "current" ? "" : "bg-card"}
            onClick={() => onModeChange("current")}
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            {currentLabel}
          </Button>
        </div>
      </div>
    </Card>
  )
}


export function RequestsWorkspace() {
  const [mode, setMode] = useState<Mode>("current")

  return (
    <>
      <ModeBar
        mode={mode}
        onModeChange={setMode}
        historyLabel="Historique importé"
        currentLabel="Nouvelles demandes"
        description="Consultez les 13 399 anciennes demandes ou créez et gérez les nouvelles demandes MaintIA."
      />
      {mode === "history" ? <HistoricalRequestsContent /> : <RequestsContent />}
    </>
  )
}


export function InterventionsWorkspace() {
  const [mode, setMode] = useState<Mode>("current")

  return (
    <>
      <ModeBar
        mode={mode}
        onModeChange={setMode}
        historyLabel="Tâches historiques"
        currentLabel="Nouvelles interventions"
        description="Consultez les 15 331 anciennes tâches ou créez et suivez les nouvelles interventions."
      />
      {mode === "history" ? <HistoricalTasksContent /> : <InterventionsContent />}
    </>
  )
}


export function StockWorkspace() {
  const [mode, setMode] = useState<Mode>("current")

  return (
    <>
      <ModeBar
        mode={mode}
        onModeChange={setMode}
        historyLabel="Demandes de fournitures"
        currentLabel="Stock actuel"
        description="Les anciennes demandes de fournitures sont séparées des quantités physiques réellement gérées dans le stock."
      />
      {mode === "history" ? <HistoricalSuppliesContent /> : <StockContent />}
    </>
  )
}


export function AnalyticsWorkspace() {
  const [mode, setMode] = useState<Mode>("history")

  return (
    <>
      <ModeBar
        mode={mode}
        onModeChange={setMode}
        historyLabel="Analyse historique"
        currentLabel="Analyse opérationnelle"
        description="Analysez l’historique importé ou les nouvelles données créées directement dans MaintIA."
      />
      {mode === "history" ? <HistoricalAnalyticsContent /> : <AnalyticsContent />}
    </>
  )
}
