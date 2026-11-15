"use client";

import { useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import { Suspense, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";

import { ForgotPasswordButton } from "./_components/ForgotPasswordButton";

/**
 * Solo aceptamos rutas internas como destino post-login. Un callbackUrl absoluto
 * (`https://…`, `//host`) sería un open redirect, y volver a `/login` o
 * `/api/auth` dejaría al usuario rebotando en la misma pantalla.
 */
function safeCallbackUrl(raw: string | null): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return "/dashboard";
  if (raw.startsWith("/login") || raw.startsWith("/api/auth")) return "/dashboard";
  return raw;
}

function LoginForm() {
  const params = useSearchParams();
  const callbackUrl = safeCallbackUrl(params.get("callbackUrl"));

  const [email, setEmail] = useState("dev@upc.edu.pe");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isPending) return;
    setError(null);
    setIsPending(true);
    try {
      const res = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });
      if (!res || res.error) {
        setError("Credenciales inválidas");
        setIsPending(false);
        return;
      }
      // Navegación completa, no router.push: el Router Cache del cliente puede
      // tener guardada la respuesta de cuando aún no había sesión (un redirect
      // del proxy a /login), y la navegación suave la reutilizaba → el usuario
      // quedaba en "Ingresando..." o de vuelta en el login. Un request nuevo
      // viaja con la cookie de sesión recién emitida y el proxy lo deja pasar.
      window.location.assign(callbackUrl);
    } catch {
      setError("No se pudo conectar. Intenta de nuevo.");
      setIsPending(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg-2 flex items-center justify-center p-4 sm:p-6">
      <div className="flex flex-col items-center gap-6 w-full max-w-[440px]">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-2xl bg-primary text-white flex items-center justify-center relative">
            <span className="absolute w-5 h-[3px] bg-white rounded-sm" />
            <span className="absolute w-[3px] h-5 bg-white rounded-sm" />
          </div>
          <div className="font-bold text-2xl tracking-[-0.5px]">
            UPC<span className="text-primary">Bot</span>
          </div>
        </div>

        <Card className="w-full p-4 sm:p-12 flex flex-col gap-7" variant="flush">
          <div className="flex flex-col gap-2 px-4 sm:px-12 pt-6 sm:pt-12 pb-0">
            <h1 className="text-[32px] font-bold tracking-[-1px] leading-tight">
              Bienvenido
            </h1>
            <p className="text-sm text-muted">
              Inicia sesión para acceder al panel administrativo de matrícula.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-4 sm:px-12">
            <Field label="Email institucional">
              <Input
                type="email"
                placeholder="admin@upc.edu.pe"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </Field>
            <Field label="Contraseña">
              <Input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </Field>
            {error && (
              <p className="text-sm text-red-600" role="alert">
                {error}
              </p>
            )}
            <div className="flex flex-col gap-3 pt-3">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full justify-center"
                disabled={isPending}
              >
                {isPending ? "Ingresando..." : "Iniciar sesión"}
              </Button>
              <ForgotPasswordButton />
            </div>
          </form>

          <div className="pb-6 sm:pb-12" />
        </Card>

        <p className="text-[11px] font-mono text-muted-2 mt-2">
          v0.1 · chatbot de matrícula · universidad peruana de ciencias aplicadas
        </p>
      </div>
    </div>
  );
}

// useSearchParams() requiere un boundary de Suspense para el prerender de Next.
export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg-2" />}>
      <LoginForm />
    </Suspense>
  );
}
