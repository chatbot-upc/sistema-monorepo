import {
  MessageSquare,
  AlertCircle,
  Zap,
  DollarSign,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  FileText,
  Plus,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { LinkIconButton } from "@/components/ui/LinkIconButton";
import { Avatar } from "@/components/ui/Avatar";
import { MiniBars } from "@/components/charts/MiniBars";
import { BigBars } from "@/components/charts/BigBars";
import { topIntents } from "@/lib/mock";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";

export default function DashboardPage() {
  const convHeights = [50, 55, 48, 65, 75, 88, 100, 92, 80, 68, 74, 62, 58, 65];
  const latHeights = [50, 62, 54, 78, 65, 90, 72, 60];

  return (
    <div className="flex flex-col gap-5 min-w-0">
      <DashboardHeader />

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Conversaciones hoy"
          value="1,247"
          color="mint"
          ratio={0.85}
          icon={<MessageSquare size={18} strokeWidth={1.75} />}
          legend={{ left: "Resueltas", right: "Activas" }}
          breakdown={{ left: "1,062", right: "142" }}
        />
        <StatCard
          label="Escaladas"
          value="43"
          color="primary"
          ratio={0.93}
          icon={<AlertCircle size={18} strokeWidth={1.75} />}
          legend={{ left: "Atendidas", right: "Pendientes" }}
          breakdown={{ left: "40", right: "3" }}
        />
        <StatCard
          label="Mensajes hoy"
          value="3,891"
          color="amber"
          ratio={0.55}
          icon={<Zap size={18} strokeWidth={1.75} />}
          legend={{ left: "Recibidos", right: "Enviados" }}
          breakdown={{ left: "2,144", right: "1,747" }}
        />
        <StatCard
          label="Costo del día"
          value="S/ 28.40"
          color="blue"
          ratio={0.88}
          icon={<DollarSign size={18} strokeWidth={1.75} />}
          legend={{ left: "Tokens IN", right: "Tokens OUT" }}
          breakdown={{ left: "142k", right: "38k" }}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-[1.4fr_1fr_1.2fr] gap-4">
        {/* Conversaciones */}
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
              8,420
            </div>
            <div className="font-mono text-[13px] text-success font-medium mt-1.5 flex items-center gap-1">
              <TrendingUp size={14} strokeWidth={2.5} />
              +18.2%
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface-2 rounded-full text-xs font-medium text-fg-2">
              <span className="font-mono font-bold text-fg">1,062</span>
              <span className="text-[11px] text-muted bg-surface px-2 py-0.5 rounded-full">
                resueltas
              </span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface-2 rounded-full text-xs font-medium text-fg-2">
              <span className="font-mono font-bold text-fg">43</span>
              <span className="text-[11px] text-muted bg-surface px-2 py-0.5 rounded-full">
                escaladas
              </span>
            </div>
          </div>
          <MiniBars
            heights={convHeights}
            highlightAt={7}
            color="mint"
            className="mt-3"
          />
        </Card>

        {/* Latencia */}
        <Card className="p-6 relative">
          <div className="flex justify-between items-start">
            <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
              Latencia
            </h3>
            <LinkIconButton
              href="/reports?focus=latency"
              variant="ghost"
              size="sm"
              aria-label="Ver detalle de latencia"
            >
              <ArrowUpRight size={14} strokeWidth={2} />
            </LinkIconButton>
          </div>
          <div className="mt-4">
            <div className="text-4xl font-bold tracking-[-0.8px] leading-none">
              1.42s
            </div>
            <div className="font-mono text-[13px] text-success font-medium mt-1.5 flex items-center gap-1">
              <TrendingDown size={14} strokeWidth={2.5} />
              -120ms p95
            </div>
          </div>
          <MiniBars
            heights={latHeights}
            highlightAt={5}
            color="blue"
            className="mt-6"
          />
        </Card>

        {/* Cola escaladas */}
        <Card className="p-6">
          <div className="flex justify-between items-start">
            <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
              Cola escaladas
            </h3>
            <LinkIconButton
              href="/conversations/mp-001?filter=escalated"
              variant="ghost"
              size="sm"
              aria-label="Ver cola de escaladas"
            >
              <ArrowUpRight size={14} strokeWidth={2} />
            </LinkIconButton>
          </div>
          <div className="text-[13px] text-muted mt-3.5">3 estudiantes esperando</div>

          <div className="flex gap-1.5 mt-3">
            <Avatar initials="JC" gradient="amber" size="md" className="!w-9 !h-9 !text-xs" />
            <Avatar initials="MP" gradient="coral" size="md" className="!w-9 !h-9 !text-xs" />
            <Avatar initials="RP" gradient="violet" size="md" className="!w-9 !h-9 !text-xs" />
            <div className="w-9 h-9 rounded-full border-2 border-dashed border-line-2 text-muted-2 flex items-center justify-center text-sm">
              +
            </div>
            <div className="w-9 h-9 rounded-full bg-surface-2" />
            <div className="w-9 h-9 rounded-full bg-surface-2" />
          </div>

          <div className="mt-4 text-[13px] text-fg font-semibold">
            Slots disponibles hoy
          </div>
          <div className="grid grid-cols-4 gap-1.5 mt-3">
            {["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"].map(
              (t, i) => (
                <div
                  key={t}
                  className={
                    i === 2
                      ? "bg-ink text-white rounded-full py-2 text-center text-[11px] font-mono font-medium"
                      : "bg-surface-2 text-fg-2 rounded-full py-2 text-center text-[11px] font-mono font-medium"
                  }
                >
                  {t}
                </div>
              )
            )}
          </div>

          <div className="mt-4 h-2 rounded-full bg-[linear-gradient(90deg,#F5A623_0%,#4ADE80_35%,#3B82F6_70%,#FAF8F4_70%)] relative">
            <div className="absolute -top-1 left-[70%] w-4 h-4 bg-surface border border-line rounded-full" />
          </div>
        </Card>
      </div>

      {/* Big chart */}
      <Card className="p-7">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-[20px] font-semibold tracking-[-0.3px]">
              Intenciones más frecuentes
            </h3>
            <div className="mt-4">
              <div className="text-[34px] font-bold tracking-[-0.8px] leading-none">
                1,247{" "}
                <span className="text-sm font-medium text-muted ml-2">
                  conversaciones · top 5
                </span>
              </div>
              <div className="font-mono text-[13px] text-primary font-medium mt-1">
                ↘ -3.5% fallback rate vs ayer
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
          <BigBars data={topIntents} yMax={1000} />
        </div>
      </Card>
    </div>
  );
}
