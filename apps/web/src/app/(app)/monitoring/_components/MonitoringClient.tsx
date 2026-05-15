"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { MiniStat } from "@/components/ui/MiniStat";
import type { MonitoringHealth } from "@/lib/api/monitoring";

const AUTO_REFRESH_MS = 10_000;

function formatMs(value: number | null): string {
  if (value === null) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

function formatPct(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(1)}%`;
}

interface MonitoringClientProps {
  initial: MonitoringHealth;
}

export function MonitoringClient({ initial }: MonitoringClientProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Auto-refresh: call router.refresh() which re-runs the Server Component fetch.
  useEffect(() => {
    const id = setInterval(() => {
      startTransition(() => {
        router.refresh();
        setLastRefresh(new Date());
      });
    }, AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, [router]);

  const refresh = () => {
    startTransition(() => {
      router.refresh();
      setLastRefresh(new Date());
    });
  };

  const { messages, intent_classifier, tokens, conversations, queue } = initial;
  const workersOk = queue.workers_alive >= 1;
  const queueOk = queue.pending >= 0 && queue.pending < 20;

  return (
    <div className="flex flex-col gap-5">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold tracking-[-0.6px] leading-none">
            Monitoreo
          </h1>
          <p className="text-sm text-muted mt-2">
            Salud del procesamiento de mensajes — uso interno
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-muted">
            Última: {lastRefresh.toLocaleTimeString("es-PE")}
            {isPending && (
              <Loader2
                size={11}
                className="inline ml-2 animate-spin"
                aria-hidden
              />
            )}
          </span>
          <Button variant="secondary" size="sm" onClick={refresh}>
            <RefreshCw size={14} strokeWidth={2.5} />
            Refrescar
          </Button>
        </div>
      </header>

      {/* Cards principales */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <MiniStat
          label="Mensajes / hora"
          value={messages.last_hour}
          trend={{
            text: `${messages.last_24h} en 24h`,
            direction: "up",
            tone: "primary",
          }}
        />
        <MiniStat
          label="Latencia p95"
          value={formatMs(messages.p95_latency_ms)}
          trend={{
            text: `avg ${formatMs(messages.avg_latency_ms)}`,
            direction:
              (messages.p95_latency_ms ?? 0) > 5000 ? "up" : "down",
            tone: (messages.p95_latency_ms ?? 0) > 5000 ? "primary" : "success",
          }}
        />
        <MiniStat
          label="Conv. abiertas"
          value={conversations.open}
          trend={{
            text: `${conversations.takeover} en takeover`,
            direction: "up",
            tone: conversations.takeover > 0 ? "primary" : "success",
          }}
        />
        <MiniStat
          label="Cerradas hoy"
          value={conversations.closed_today}
        />
        <MiniStat
          label="Tokens (hoy)"
          value={(tokens.input_today + tokens.output_today).toLocaleString("es-PE")}
          trend={{
            text: `${tokens.input_today.toLocaleString("es-PE")} in / ${tokens.output_today.toLocaleString("es-PE")} out`,
            direction: "up",
            tone: "success",
          }}
        />
        <MiniStat
          label="Cola pendiente"
          value={queue.pending < 0 ? "—" : queue.pending}
          trend={{
            text: `${queue.workers_alive} worker${queue.workers_alive === 1 ? "" : "s"}`,
            direction: workersOk && queueOk ? "down" : "up",
            tone: workersOk && queueOk ? "success" : "primary",
          }}
        />
      </div>

      {/* Intent classifier breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-6 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-[12px] uppercase tracking-[0.6px] font-semibold text-muted">
            <Activity size={14} strokeWidth={2} />
            Clasificador de intenciones (24h)
          </div>
          <div className="grid grid-cols-3 gap-4 mt-2">
            <div>
              <div className="text-[11px] text-muted uppercase tracking-[0.6px] font-semibold">
                Mensajes
              </div>
              <div className="text-2xl font-semibold tabular mt-1">
                {intent_classifier.classified_last_24h}
              </div>
            </div>
            <div>
              <div className="text-[11px] text-muted uppercase tracking-[0.6px] font-semibold">
                Solo SBERT
              </div>
              <div className="text-2xl font-semibold tabular text-success mt-1">
                {formatPct(intent_classifier.sbert_only_pct)}
              </div>
            </div>
            <div>
              <div className="text-[11px] text-muted uppercase tracking-[0.6px] font-semibold">
                Fallback LLM
              </div>
              <div className="text-2xl font-semibold tabular text-primary mt-1">
                {formatPct(intent_classifier.fallback_to_llm_pct)}
              </div>
            </div>
          </div>
          {intent_classifier.fallback_to_llm_pct !== null &&
            intent_classifier.fallback_to_llm_pct > 40 && (
              <div className="flex items-center gap-2 text-[12px] text-amber-fg bg-amber-soft px-3 py-2 rounded-lg">
                <AlertTriangle size={14} strokeWidth={2} />
                Tasa de fallback alta — considera enriquecer ejemplos de
                intents o bajar el umbral.
              </div>
            )}
        </Card>

        <Card className="p-6 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-[12px] uppercase tracking-[0.6px] font-semibold text-muted">
            <CheckCircle2 size={14} strokeWidth={2} />
            Salud del stack
          </div>
          <ul className="flex flex-col gap-2 mt-2 text-[13px]">
            <HealthRow
              ok={workersOk}
              label="Celery worker"
              value={`${queue.workers_alive} activo${queue.workers_alive === 1 ? "" : "s"}`}
            />
            <HealthRow
              ok={queueOk}
              label="Cola Redis"
              value={
                queue.pending < 0
                  ? "no disponible"
                  : `${queue.pending} pendiente${queue.pending === 1 ? "" : "s"}`
              }
            />
            <HealthRow
              ok={(messages.p95_latency_ms ?? 0) < 5000}
              label="Latencia p95"
              value={formatMs(messages.p95_latency_ms)}
            />
          </ul>
        </Card>
      </div>
    </div>
  );
}

function HealthRow({
  ok,
  label,
  value,
}: {
  ok: boolean;
  label: string;
  value: string;
}) {
  return (
    <li className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-fg">
        {ok ? (
          <CheckCircle2 size={14} strokeWidth={2.5} className="text-success" />
        ) : (
          <AlertTriangle size={14} strokeWidth={2.5} className="text-primary" />
        )}
        {label}
      </span>
      <span className="font-mono text-[12px] text-muted">{value}</span>
    </li>
  );
}
