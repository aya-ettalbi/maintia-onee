import { AlertCircle } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

export function ErrorBanner({ message }: { message: string }) {
  return (
    <Alert variant="destructive" className="rounded-xl">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Impossible de terminer l’opération</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  )
}
