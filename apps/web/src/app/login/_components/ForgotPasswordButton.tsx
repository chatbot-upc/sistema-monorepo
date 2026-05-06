"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Mail } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";

export function ForgotPasswordButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-[13px] text-muted hover:text-primary transition-colors cursor-pointer"
      >
        ¿Olvidaste tu contraseña?
      </button>
      <ForgotPasswordModal open={open} onOpenChange={setOpen} />
    </>
  );
}

interface ForgotPasswordModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

const isValidEmail = (s: string) => {
  const t = s.trim();
  return t.length > 0 && t.includes("@");
};

function ForgotPasswordModal({ open, onOpenChange }: ForgotPasswordModalProps) {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  // Cancel guard para descartar mutaciones si el modal se cierra mid-await.
  // Vercel rule: rerender-use-ref-transient-values.
  const cancelRef = useRef(false);

  useEffect(() => {
    if (open) {
      setEmail("");
      setSent(false);
      setSubmitting(false);
      cancelRef.current = false;
      return () => {
        cancelRef.current = true;
      };
    }
  }, [open]);

  const submit = async () => {
    if (submitting || !isValidEmail(email)) return;
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 600));
    if (cancelRef.current) return;
    setSubmitting(false);
    setSent(true);
  };

  const icon = (
    <div className="w-9 h-9 rounded-full bg-primary-soft flex items-center justify-center">
      {sent ? (
        <CheckCircle2 size={18} className="text-success" strokeWidth={2} />
      ) : (
        <Mail size={18} className="text-primary" strokeWidth={2} />
      )}
    </div>
  );

  return (
    <Modal open={open} onOpenChange={onOpenChange} size="sm">
      <Modal.Header
        title={sent ? "Revisa tu correo" : "Recuperar contraseña"}
        description={
          sent
            ? "Te enviamos un enlace para restablecer tu contraseña."
            : "Ingresa tu email institucional. Te enviaremos un enlace para restablecer tu contraseña."
        }
        icon={icon}
      />
      <Modal.Body className="min-h-[88px]">
        {sent ? (
          <div className="text-[13px] text-fg-2 leading-relaxed">
            Si{" "}
            <span className="font-mono font-semibold text-fg">
              {email.trim()}
            </span>{" "}
            está registrado, recibirás el correo en los próximos minutos.
          </div>
        ) : (
          <Field label="Email institucional">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@upc.edu.pe"
              autoFocus
              onKeyDown={(e) => {
                if (e.key !== "Enter") return;
                if (submitting || !isValidEmail(email)) return;
                submit();
              }}
            />
          </Field>
        )}
      </Modal.Body>
      <Modal.Footer>
        {sent ? (
          <Button variant="primary" onClick={() => onOpenChange(false)}>
            Entendido
          </Button>
        ) : (
          <>
            <Button
              variant="secondary"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={submit}
              disabled={submitting || !isValidEmail(email)}
            >
              {submitting ? "Enviando..." : "Enviar enlace"}
            </Button>
          </>
        )}
      </Modal.Footer>
    </Modal>
  );
}
