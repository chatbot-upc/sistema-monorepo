import { apiFetch } from "./client";

export interface MonitoringHealth {
  messages: {
    last_hour: number;
    last_24h: number;
    avg_latency_ms: number | null;
    p95_latency_ms: number | null;
  };
  intent_classifier: {
    classified_last_24h: number;
    sbert_only_pct: number | null;
    fallback_to_llm_pct: number | null;
  };
  tokens: {
    input_today: number;
    output_today: number;
  };
  conversations: {
    open: number;
    takeover: number;
    closed_today: number;
  };
  queue: {
    pending: number;
    workers_alive: number;
  };
}

export async function fetchMonitoringHealth(): Promise<MonitoringHealth> {
  return apiFetch<MonitoringHealth>("/api/v1/monitoring/health");
}
