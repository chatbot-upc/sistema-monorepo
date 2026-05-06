import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { ForgotPasswordButton } from "./_components/ForgotPasswordButton";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-bg-2 flex items-center justify-center p-6">
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

        <Card className="w-full p-12 flex flex-col gap-7" variant="flush">
          <div className="flex flex-col gap-2 px-12 pt-12 pb-0">
            <h1 className="text-[32px] font-bold tracking-[-1px] leading-tight">
              Bienvenido
            </h1>
            <p className="text-sm text-muted">
              Inicia sesión para acceder al panel administrativo de matrícula.
            </p>
          </div>

          <form className="flex flex-col gap-4 px-12">
            <Field label="Email institucional">
              <Input
                type="email"
                placeholder="admin@upc.edu.pe"
                defaultValue="admin@upc.edu.pe"
              />
            </Field>
            <Field label="Contraseña">
              <Input type="password" placeholder="••••••••" />
            </Field>
          </form>

          <div className="flex flex-col gap-3 px-12 pb-12">
            <Link href="/dashboard">
              <Button variant="primary" size="lg" className="w-full justify-center">
                Iniciar sesión
              </Button>
            </Link>
            <ForgotPasswordButton />
          </div>
        </Card>

        <p className="text-[11px] font-mono text-muted-2 mt-2">
          v0.1 · chatbot de matrícula · universidad peruana de ciencias aplicadas
        </p>
      </div>
    </div>
  );
}
