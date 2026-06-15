import Link from "next/link";
import Image from "next/image";

const WA_NUMBER = "51989344521";
const WA_LINK = `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(
  "Hola Remi, tengo una consulta sobre mi matrícula"
)}`;

function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M.057 24l1.687-6.163a11.867 11.867 0 0 1-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.817 11.817 0 0 1 8.413 3.488 11.824 11.824 0 0 1 3.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 0 1-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 0 0 1.523 5.26l-.999 3.648 3.965-1.607zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.5-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413z" />
    </svg>
  );
}

const askables = [
  "¿Hasta cuándo puedo matricularme?",
  "¿Qué cursos me toca llevar este ciclo?",
  "¿Cómo pido una rectificación?",
  "¿Tengo deudas que me bloqueen?",
  "¿Cuándo publican los horarios?",
  "¿Qué requisitos necesito para matricularme?",
  "¿Dónde veo mi malla curricular?",
  "¿Cómo cambio de carrera?",
];

const chat = [
  { from: "user", text: "Hola, ¿hasta cuándo puedo matricularme este ciclo?" },
  {
    from: "bot",
    text: "¡Hola! 👋 La matrícula regular va del 10 al 24 de marzo. Después solo queda extemporánea con recargo. ¿Te explico los pasos?",
  },
  { from: "user", text: "Sí porfa 🙏" },
  {
    from: "bot",
    text: "Necesitas: 1) no tener deudas, 2) tu plan de estudios al día y 3) ingresar al portal con tu código. ¿Te ayudo con alguno?",
  },
];

const steps = [
  {
    t: "Abre el chat",
    d: "Toca el botón y se abre WhatsApp con Remi, listo para atenderte.",
  },
  {
    t: "Escribe tu duda",
    d: "Pregunta como le escribirías a un compañero. Sin formularios ni códigos.",
  },
  {
    t: "Recibe la respuesta",
    d: "Remi te responde al toque y, si hace falta, te pasa con un asesor.",
  },
];

export default function Home() {
  return (
    <main className="overflow-x-hidden">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-line/80 bg-bg/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5">
          <Link href="/" className="flex items-center gap-2.5">
            <Image
              src="/logo-remi.png"
              alt="Remi"
              width={36}
              height={36}
              className="h-8 w-8 object-contain"
              priority
            />
            <span className="display text-lg">Remi</span>
          </Link>
          <a
            href={WA_LINK}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-on-brand transition-colors hover:bg-brand-deep"
          >
            <WhatsAppIcon className="h-4 w-4" />
            Escribir a Remi
          </a>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-14 pt-14 md:grid-cols-[1.04fr_0.96fr] md:gap-8 md:pb-24 md:pt-20">
        {/* Left */}
        <div>
          <span
            className="rise inline-flex items-center gap-2 rounded-full bg-brand-soft px-3 py-1.5 text-[13px] font-semibold text-brand-deep"
            style={{ animationDelay: "40ms" }}
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-wa opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-wa" />
            </span>
            Responde al instante · 24/7
          </span>

          <h1
            className="rise display mt-5 text-[clamp(2.4rem,6vw,4.2rem)] leading-[1.04] text-ink"
            style={{ animationDelay: "100ms" }}
          >
            Tu matrícula,
            <br />
            resuelta por{" "}
            <span className="whitespace-nowrap text-brand">WhatsApp</span>.
          </h1>

          <p
            className="rise prose-pretty mt-5 max-w-md text-lg leading-relaxed text-ink-2"
            style={{ animationDelay: "160ms" }}
          >
            Remi es el asistente que responde tus dudas de matrícula, cursos y
            trámites al toque. Sin filas, sin esperas, sin descargar nada.
          </p>

          <div
            className="rise mt-8 flex flex-wrap items-center gap-3"
            style={{ animationDelay: "220ms" }}
          >
            <a
              href={WA_LINK}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2.5 rounded-full bg-brand px-6 py-3.5 font-semibold text-on-brand shadow-[0_10px_30px_-12px_rgba(213,0,0,0.65)] transition-transform duration-200 hover:-translate-y-0.5"
            >
              <WhatsAppIcon className="h-5 w-5" />
              Iniciar conversación
            </a>
            <a
              href="#preguntas"
              className="inline-flex items-center gap-2 rounded-full border border-line-2 px-5 py-3.5 font-semibold text-ink-2 transition-colors hover:border-ink/25 hover:text-ink"
            >
              Qué le puedes preguntar
            </a>
          </div>
        </div>

        {/* Right — chat */}
        <div
          className="rise relative mx-auto w-full max-w-[360px]"
          style={{ animationDelay: "180ms" }}
        >
          <div className="floaty">
            <div className="rounded-[24px] border border-line-2 bg-surface p-2.5 shadow-[0_30px_60px_-28px_rgba(23,21,26,0.4)]">
              <div className="overflow-hidden rounded-[16px] border border-line">
                {/* header */}
                <div className="flex items-center gap-3 bg-brand px-4 py-3">
                  <span className="grid h-10 w-10 place-items-center overflow-hidden rounded-full bg-white ring-2 ring-white/30">
                    <Image
                      src="/logo-remi.png"
                      alt="Remi"
                      width={32}
                      height={32}
                      className="h-8 w-8 object-contain"
                    />
                  </span>
                  <div className="leading-tight">
                    <p className="text-sm font-semibold text-on-brand">Remi</p>
                    <p className="flex items-center gap-1.5 text-[11px] text-on-brand/85">
                      <span className="h-1.5 w-1.5 rounded-full bg-wa" />
                      en línea
                    </p>
                  </div>
                  <WhatsAppIcon className="ml-auto h-5 w-5 text-on-brand/70" />
                </div>
                {/* messages */}
                <div className="space-y-2 bg-bg-2 px-3.5 py-5">
                  {chat.map((m, i) => (
                    <div
                      key={i}
                      className={
                        "bubble-in text-[13px] leading-snug " +
                        (m.from === "user"
                          ? "ml-auto max-w-[84%] rounded-2xl rounded-tr-sm bg-brand px-3.5 py-2.5 text-on-brand"
                          : "mr-auto max-w-[84%] rounded-2xl rounded-tl-sm border border-line bg-surface px-3.5 py-2.5 text-ink")
                      }
                      style={{ animationDelay: `${450 + i * 420}ms` }}
                    >
                      {m.text}
                    </div>
                  ))}
                  <div
                    className="bubble-in mr-auto flex max-w-[84%] items-center gap-1 rounded-2xl rounded-tl-sm border border-line bg-surface px-4 py-3"
                    style={{ animationDelay: "2300ms" }}
                  >
                    <Dot delay="0ms" />
                    <Dot delay="200ms" />
                    <Dot delay="400ms" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* What you can ask — chat-native, no card grid */}
      <section
        id="preguntas"
        className="border-t border-line bg-bg-2/60 py-20 md:py-28"
      >
        <div className="mx-auto max-w-5xl px-5">
          <h2 className="display max-w-2xl text-3xl leading-tight text-ink sm:text-[2.6rem]">
            Pregúntale como le escribirías{" "}
            <span className="text-brand">a un amigo</span>.
          </h2>
          <p className="prose-pretty mt-4 max-w-lg text-lg text-ink-2">
            Sin palabras clave ni menús. Remi entiende lo que necesitas y te
            responde con información académica al día.
          </p>

          <ul className="mt-10 flex flex-wrap gap-3">
            {askables.map((q) => (
              <li
                key={q}
                className="rounded-2xl rounded-tl-sm border border-line-2 bg-surface px-4 py-3 text-[15px] text-ink-2 shadow-sm transition-colors hover:border-brand/40 hover:text-ink"
              >
                {q}
              </li>
            ))}
          </ul>

          <div className="mt-12 flex flex-wrap items-center gap-x-8 gap-y-3 text-[15px] text-ink-2">
            <span className="inline-flex items-center gap-2">
              <Check /> Disponible a cualquier hora
            </span>
            <span className="inline-flex items-center gap-2">
              <Check /> Información académica oficial
            </span>
            <span className="inline-flex items-center gap-2">
              <Check /> Te deriva con un asesor si hace falta
            </span>
          </div>
        </div>
      </section>

      {/* How it works — a real 3-step sequence */}
      <section className="mx-auto max-w-5xl px-5 py-20 md:py-28">
        <h2 className="display text-3xl leading-tight text-ink sm:text-[2.6rem]">
          Tan simple como abrir un chat
        </h2>
        <ol className="mt-12 grid gap-x-8 gap-y-10 sm:grid-cols-3">
          {steps.map((s, i) => (
            <li key={s.t} className="relative">
              <div className="flex items-center gap-3">
                <span className="display grid h-9 w-9 place-items-center rounded-full bg-brand text-base text-on-brand">
                  {i + 1}
                </span>
                {i < steps.length - 1 && (
                  <span className="hidden h-px flex-1 bg-line-2 sm:block" />
                )}
              </div>
              <h3 className="display mt-5 text-xl text-ink">{s.t}</h3>
              <p className="prose-pretty mt-2 text-[15px] leading-relaxed text-ink-2">
                {s.d}
              </p>
            </li>
          ))}
        </ol>
      </section>

      {/* CTA — committed red */}
      <section className="bg-brand text-on-brand">
        <div className="mx-auto max-w-4xl px-5 py-20 text-center md:py-28">
          <Image
            src="/logo-remi.png"
            alt=""
            width={56}
            height={56}
            className="mx-auto h-12 w-12 rounded-2xl bg-white p-1.5 object-contain shadow-lg"
          />
          <h2 className="display mx-auto mt-7 max-w-2xl text-[clamp(2.1rem,5vw,3.4rem)] leading-[1.05]">
            Deja de adivinar tu matrícula.
          </h2>
          <p className="prose-pretty mx-auto mt-4 max-w-md text-lg text-on-brand/85">
            Una pregunta, una respuesta clara. Remi te espera en WhatsApp.
          </p>
          <a
            href={WA_LINK}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-9 inline-flex items-center gap-2.5 rounded-full bg-white px-7 py-4 font-semibold text-brand shadow-xl transition-transform duration-200 hover:-translate-y-0.5"
          >
            <WhatsAppIcon className="h-5 w-5" />
            Hablar con Remi ahora
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 text-sm text-muted sm:flex-row">
          <div className="flex items-center gap-2.5">
            <Image
              src="/logo-remi.png"
              alt="Remi"
              width={26}
              height={26}
              className="h-6 w-6 object-contain"
            />
            <span className="display text-base text-ink-2">Remi</span>
          </div>
          <p>© {new Date().getFullYear()} Remi · Asistente de matrícula</p>
          <Link
            href="/privacidad"
            className="underline-offset-4 transition-colors hover:text-ink hover:underline"
          >
            Política de privacidad
          </Link>
        </div>
      </footer>
    </main>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="h-2 w-2 rounded-full bg-muted"
      style={{ animation: "blink 1.3s ease-in-out infinite", animationDelay: delay }}
    />
  );
}

function Check() {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      className="h-5 w-5 shrink-0 text-brand"
      aria-hidden
    >
      <path
        d="M4 10.5l3.5 3.5L16 6"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
