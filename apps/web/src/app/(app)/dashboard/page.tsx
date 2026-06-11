import {
  MessageSquare,
  AlertCircle,
  Zap,
  TrendingUp,
  ArrowUpRight,
  FileText,
  Plus,
  Gauge,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { LinkIconButton } from "@/components/ui/LinkIconButton";
import { Avatar } from "@/components/ui/Avatar";
import { MiniBars } from "@/components/charts/MiniBars";
import { BigBars } from "@/components/charts/BigBars";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import {
  fetchConversationsByDay,
  fetchDashboard,
  fetchIntentDistribution,
} from "@/lib/api/reports";
import { fetchConversations } from "@/lib/api/conversations";

type BarColor = "primary" | "coral" | "amber" | "violet" | "blue" | "mint";
const BAR_COLORS: BarColor[] = ["coral", "amber", "primary", "violet", "blue"];
const AVATAR_GRADIENTS = ["amber", "coral", "violet", "mint", "blue", "rose"] as const;

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function isoToday(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Normaliza una lista de conteos a alturas 0-100 para MiniBars. */
function toHeights(counts: number[]): number[] {
  const max = Math.max(...counts, 1);
  return counts.map((c) => Math.round((c / max) * 100));
}

/** Alinea los conteos por día a una ventana fija de `len` días (rellena con 0). */
function padToWindow(rows: { date: string; count: number }[], len: number): number[] {
  const byDate = new Map(rows.map((r) => [r.date, r.count]));
  const out: number[] = [];
  for (let i = len - 1; i >= 0; i--) {
    out.push(byDate.get(isoDaysAgo(i)) ?? 0);
  }
  return out;
}

function initialsOf(name: string | null, phone: string): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
  }
  return phone.slice(-2);
}

export default async function DashboardPage() {
  const [stats, convByDay, intents, escalatedQueue] = await Promise.all([
    fetchDashboard(),
    fetchConversationsByDay(isoDaysAgo(6), isoToday()),
    fetchIntentDistribution(isoDaysAgo(29), isoToday()),
    fetchConversations({ status: "takeover", size: 8 }),
  ]);

  const convCounts = padToWindow(convByDay, 7);
  const convTotal7d = convCounts.reduce((a, b) => a + b, 0);
  const convHeights = toHeights(convCounts);

  const topIntents = intents.slice(0, 5).map((it, i) => ({
    name: it.intent_name,
    value: it.count,
    color: BAR_COLORS[i % BAR_COLORS.length],
  }));
  const intentYMax = Math.max(...topIntents.map((t) => t.value), 1);
  const intentTotal = intents.reduce((a, b) => a + b.count, 0);

  const certezaPct =
    stats.avg_confidence > 0 ? `${(stats.avg_confidence * 100).toFixed(1)}%` : "—";
  const latencia =
    stats.avg_latency_ms != null
      ? `${(stats.avg_latency_ms / 1000).toFixed(2)}s`
      : "—";

  return (
    <div className="flex flex-col gap-5 min-w-0">
      <DashboardHeader />

      {/* KPIs de la HU: activas, escaladas, tema top, certeza */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Conversaciones activas"
          value={String(stats.conversations_active)}
          color="mint"
          ratio={0.85}
          icon={<MessageSquare size={18} strokeWidth={1.75} />}
        />
        <StatCard
          label="Escaladas"
          value={String(stats.conversations_escalated)}
          color="primary"
          ratio={0.9}
          icon={<AlertCircle size={18} strokeWidth={1.75} />}
        />
        <StatCard
          label="Tema top del día"
          value={stats.top_intent?.name ?? "—"}
          color="amber"
          ratio={0.7}
          icon={<TrendingUp size={18} strokeWidth={1.75} />}
          breakdown={
            stats.top_intent
              ? { left: `${stats.top_intent.count}`, right: "detecciones" }
              : undefined
          }
        />
        <StatCard
          label="Certeza promedio"
          value={certezaPct}
          color="blue"
          ratio={stats.avg_confidence || 0.5}
          icon={<Zap size={18} strokeWidth={1.75} />}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-[1.4fr_1fr_1.2fr] gap-4">
        {/* Conversaciones (últimos 7 días) */}
        <Card className="p-6 relative">
          <div className="flex justify-between items-start">
            <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
              Conversaciones
            </h3>
            <LinkIconButton
              href="/reports?focus=conversations"
              variant="ghost"
              size="sm"
              aria-label="Ver detalle de conversaciones"
            >
              <ArrowUpRight size={14} strokeWidth={2} />
            </LinkIconButton>
          </div>
          <div className="mt-4">
            <div className="text-xs text-muted">Últimos 7 días</div>
            <div className="text-4xl font-bold tracking-[-0.8px] tabular leading-none mt-1">
              {convTotal7d.toLocaleString("es-PE")}
            </div>
            <div className="font-mono text-[13px] text-muted font-medium mt-1.5">
              {stats.conversations_today} hoy
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface-2 rounded-full text-xs font-medium text-fg-2">
              <span className="font-mono font-bold text-fg">
                {stats.conversations_active}
              </span>
              <span className="text-[11px] text-muted bg-surface px-2 py-0.5 rounded-full">
                activas
              </span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface-2 rounded-full text-xs font-medium text-fg-2">
              <span className="font-mono font-bold text-fg">
                {stats.conversations_escalated}
              </span>
              <span className="text-[11px] text-muted bg-surface px-2 py-0.5 rounded-full">
                escaladas
              </span>
            </div>
          </div>
          {convTotal7d > 0 ? (
            <MiniBars
              heights={convHeights}
              highlightAt={convHeights.length - 1}
              color="mint"
              className="mt-3"
            />
          ) : (
            <div className="mt-4 text-[12px] text-muted-2">
              Sin actividad en los últimos 7 días.
            </div>
          )}
        </Card>

        {/* Latencia */}
        <Card className="p-6 relative">
          <div className="flex justify-between items-start">
            <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
              Latencia
            </h3>
            <div className="w-8 h-8 rounded-full bg-blue-soft text-blue flex items-center justify-center">
              <Gauge size={15} strokeWidth={2} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-xs text-muted">Promedio de respuesta hoy</div>
            <div className="text-4xl font-bold tracking-[-0.8px] leading-none mt-1">
              {latencia}
            </div>
            <div className="font-mono text-[13px] text-muted font-medium mt-1.5">
              {stats.messages_today} mensajes hoy
            </div>
          </div>
        </Card>

        {/* Cola escaladas */}
        <Card className="p-6">
          <div className="flex justify-between items-start">
            <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
              Cola escaladas
            </h3>
            <LinkIconButton
              href="/conversations?status=takeover"
              variant="ghost"
              size="sm"
              aria-label="Ver cola de escaladas"
            >
              <ArrowUpRight size={14} strokeWidth={2} />
            </LinkIconButton>
          </div>
          <div className="text-[13px] text-muted mt-3.5">
            {escalatedQueue.total === 0
              ? "Sin escaladas pendientes"
              : `${escalatedQueue.total} ${
                  escalatedQueue.total === 1 ? "estudiante" : "estudiantes"
                } en atención`}
          </div>

          {escalatedQueue.items.length > 0 && (
            <div className="flex gap-1.5 mt-3 flex-wrap">
              {escalatedQueue.items.map((c, i) => (
                <Avatar
                  key={c.id}
                  initials={initialsOf(c.display_name, c.student_phone)}
                  gradient={AVATAR_GRADIENTS[i % AVATAR_GRADIENTS.length]}
                  size="md"
                  className="!w-9 !h-9 !text-xs"
                />
              ))}
            </div>
          )}

          <ul className="mt-4 flex flex-col gap-2">
            {escalatedQueue.items.slice(0, 4).map((c) => (
              <li
                key={c.id}
                className="flex items-center justify-between text-[13px]"
              >
                <span className="font-medium truncate">
                  {c.display_name ?? c.student_phone}
                </span>
                <span className="font-mono text-[11px] text-muted">
                  {c.message_count} msg
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Big chart — intenciones */}
      <Card className="p-7">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-[20px] font-semibold tracking-[-0.3px]">
              Intenciones más frecuentes
            </h3>
            <div className="mt-4">
              <div className="text-[34px] font-bold tracking-[-0.8px] leading-none">
                {intentTotal.toLocaleString("es-PE")}{" "}
                <span className="text-sm font-medium text-muted ml-2">
                  detecciones · top {topIntents.length} · 30 días
                </span>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <LinkIconButton
              href="/reports?focus=intents"
              variant="ghost"
              size="md"
              aria-label="Ver intenciones en reportes"
            >
              <FileText size={16} strokeWidth={2} />
            </LinkIconButton>
            <LinkIconButton
              href="/intents?new=1"
              variant="dark"
              size="md"
              aria-label="Crear nueva intención"
            >
              <Plus size={16} strokeWidth={2} />
            </LinkIconButton>
          </div>
        </div>

        <div className="mt-8">
          {topIntents.length > 0 ? (
            <BigBars data={topIntents} yMax={intentYMax} />
          ) : (
            <div className="text-center text-muted text-sm py-16">
              Aún no hay intenciones detectadas en el período.
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
