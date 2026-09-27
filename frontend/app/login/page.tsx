"use client"

import { useEffect, useState, type FormEvent } from "react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import {
  ArrowRight,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react"
import { toast } from "sonner"

import { useAuth } from "@/components/auth/auth-provider"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"

export default function LoginPage() {
  const { login, user, loading } = useAuth()
  const router = useRouter()

  const [email, setEmail] = useState("admin@onee.ma")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && user) {
      router.replace("/")
    }
  }, [loading, router, user])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    setSubmitting(true)
    setError(null)

    try {
      await login(email.trim(), password)
      toast.success("Connexion réussie")
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.detail
          : "Impossible de se connecter au backend."
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,oklch(0.92_0.05_155),transparent_35%),var(--background)] p-3 sm:p-5">
      <div className="mx-auto grid min-h-[calc(100vh-1.5rem)] max-w-7xl overflow-hidden rounded-[2rem] border bg-card shadow-2xl sm:min-h-[calc(100vh-2.5rem)] lg:grid-cols-[1.08fr_0.92fr]">

        {/* ============================= */}
        {/* IMAGE ONEE À GAUCHE */}
        {/* ============================= */}

        <section className="relative hidden min-h-full overflow-hidden lg:block">
          <Image
            src="/onee-login-left.png"
            alt="Office National de l'Électricité et de l'Eau Potable"
            fill
            priority
            sizes="55vw"
            className="object-cover object-top"
          />
        </section>

        {/* ============================= */}
        {/* CONNEXION À DROITE */}
        {/* ============================= */}

        <section className="flex items-center justify-center p-6 sm:p-10 lg:p-14">
          <div className="w-full max-w-md">

            <div className="mb-7">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <ShieldCheck className="h-6 w-6" />
              </div>

              <h2 className="text-3xl font-black tracking-tight">
                Bienvenue
              </h2>

              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Connectez-vous avec votre compte ONEE. Les pages et les actions
                sont adaptées automatiquement à votre rôle.
              </p>
            </div>

            <Card className="border-border/80 p-5 shadow-sm">
              <form onSubmit={handleSubmit} className="space-y-5">

                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* EMAIL */}

                <div className="space-y-2">
                  <Label htmlFor="email">
                    Adresse email
                  </Label>

                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    autoComplete="username"
                    placeholder="nom@onee.ma"
                    required
                    className="h-11"
                  />
                </div>

                {/* PASSWORD */}

                <div className="space-y-2">
                  <Label htmlFor="password">
                    Mot de passe
                  </Label>

                  <div className="relative">

                    <LockKeyhole className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      autoComplete="current-password"
                      placeholder="Votre mot de passe"
                      required
                      className="h-11 pl-9 pr-11"
                    />

                    <button
                      type="button"
                      onClick={() =>
                        setShowPassword((value) => !value)
                      }
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                      aria-label={
                        showPassword
                          ? "Masquer le mot de passe"
                          : "Afficher le mot de passe"
                      }
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>

                  </div>
                </div>

                {/* BUTTON */}

                <Button
                  type="submit"
                  disabled={submitting}
                  className="h-11 w-full shadow-lg shadow-primary/20"
                >
                  {submitting ? (
                    <>
                      <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                      Connexion…
                    </>
                  ) : (
                    <>
                      Se connecter
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>

              </form>
            </Card>

            <p className="mt-5 text-center text-xs text-muted-foreground">
              Authentification JWT · Contrôle des rôles côté Backend · Session
              locale sécurisée
            </p>

          </div>
        </section>

      </div>
    </div>
  )
}