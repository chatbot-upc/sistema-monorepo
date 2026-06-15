import Link from "next/link";
import Image from "next/image";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Política de privacidad · Remi",
  description:
    "Cómo Remi recopila, usa y protege tus datos cuando conversas por WhatsApp.",
};

const sections = [
  {
    h: "1. Quiénes somos",
    p: [
      "Remi es un asistente virtual de orientación académica que atiende consultas sobre matrícula, carreras y trámites a través de WhatsApp. Esta política explica cómo tratamos la información que compartes al conversar con Remi.",
    ],
  },
  {
    h: "2. Qué datos recopilamos",
    p: ["Recopilamos únicamente la información necesaria para atender tu consulta:"],
    list: [
      "Tu número de teléfono de WhatsApp, para poder responderte.",
      "El nombre de perfil que muestra WhatsApp.",
      "El contenido de los mensajes que nos envías durante la conversación.",
    ],
  },
  {
    h: "3. Cómo usamos tus datos",
    p: ["Utilizamos tu información exclusivamente para:"],
    list: [
      "Responder tus consultas de matrícula y trámites académicos.",
      "Derivar tu caso a un asesor humano cuando se requiera atención personalizada.",
      "Mejorar la calidad y precisión de las respuestas del asistente.",
    ],
  },
  {
    h: "4. Mensajería por WhatsApp",
    p: [
      "Remi opera sobre la plataforma de WhatsApp Business, propiedad de Meta. El envío y recepción de mensajes está sujeto también a las políticas de privacidad de WhatsApp y Meta. No enviamos mensajes promocionales sin tu consentimiento previo.",
    ],
  },
  {
    h: "5. Con quién compartimos tus datos",
    p: [
      "No vendemos ni alquilamos tus datos. La información solo se comparte con el equipo académico responsable de atender tu consulta y con los proveedores tecnológicos que hacen funcionar el servicio (por ejemplo, infraestructura de mensajería y procesamiento de lenguaje), siempre bajo obligaciones de confidencialidad.",
    ],
  },
  {
    h: "6. Conservación de los datos",
    p: [
      "Conservamos el historial de conversación durante el tiempo necesario para dar seguimiento a tu consulta y cumplir obligaciones legales. Luego, los datos se eliminan o anonimizan.",
    ],
  },
  {
    h: "7. Tus derechos",
    p: [
      "Puedes solicitar en cualquier momento el acceso, la rectificación o la eliminación de tus datos escribiéndonos por el mismo canal de WhatsApp o al correo de contacto indicado abajo.",
    ],
  },
  {
    h: "8. Contacto",
    p: [
      "Si tienes preguntas sobre esta política o sobre el tratamiento de tus datos, escríbenos a: contacto@remi.pe",
    ],
  },
];

export default function Privacidad() {
  return (
    <main className="mx-auto max-w-2xl px-5 py-14">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="text-sm text-ink-2 underline-offset-4 transition-colors hover:text-ink hover:underline"
        >
          ← Volver al inicio
        </Link>
        <Image
          src="/logo-remi.png"
          alt="Remi"
          width={32}
          height={32}
          className="h-8 w-8 object-contain"
        />
      </div>

      <h1 className="display mt-10 text-4xl">Política de privacidad</h1>
      <p className="mt-3 text-sm text-muted">
        Última actualización: 13 de junio de 2026
      </p>

      <div className="mt-12 space-y-9">
        {sections.map((s) => (
          <section key={s.h}>
            <h2 className="display text-xl">{s.h}</h2>
            {s.p.map((para, i) => (
              <p key={i} className="mt-2.5 text-[15px] leading-relaxed text-ink-2">
                {para}
              </p>
            ))}
            {s.list && (
              <ul className="mt-3.5 space-y-2 pl-1">
                {s.list.map((li, i) => (
                  <li
                    key={i}
                    className="flex gap-3 text-[15px] leading-relaxed text-ink-2"
                  >
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                    {li}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>

      <div className="mt-14 border-t border-line pt-7 text-sm text-muted">
        © {new Date().getFullYear()} Remi · Asistente de matrícula
      </div>
    </main>
  );
}
