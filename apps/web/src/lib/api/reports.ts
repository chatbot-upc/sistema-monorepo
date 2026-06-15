import { apiFetch } from "./client";

export interface TopIntent {
  name: string;
  count: number;
}

export interface DashboardStats {
  conversations_total: number;
  conversations_open: number;
  conversations_active: number;
  conversations_escalated: number;
  conversations_today: number;
  messages_today: number;
  documents_indexed: number;
  intents_active: number;
  top_intent: TopIntent | null;
  avg_confidence: number;
  avg_latency_ms: number | null;
}

export interface DayCount {
  date: string;
  count: number;
}

export interface IntentSlice {
  intent_name: string;
  count: number;
  percentage: number;
}

export interface ReportSummary {
  total: number;
  total_change_pct: number | null;
  resolved_by_bot: number;
  resolved_pct_of_total: number;
  escalated: number;
  escalated_pct_of_total: number;
  fallback_rate: number;
  fallback_change_pp: number | null;
}

export async function fetchDashboard(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/api/v1/reports/dashboard");
}

export async function fetchReportSummary(
  fromDate: string,
  toDate: string,
): Promise<ReportSummary> {
  return apiFetch<ReportSummary>("/api/v1/reports/summary", {
    searchParams: { from_date: fromDate, to_date: toDate },
  });
}

export async function fetchConversationsByDay(
  fromDate: string,
  toDate: string,
): Promise<DayCount[]> {
  return apiFetch<DayCount[]>("/api/v1/reports/conversations", {
    searchParams: { from_date: fromDate, to_date: toDate },
  });
}

export async function fetchIntentDistribution(
  fromDate: string,
  toDate: string,
): Promise<IntentSlice[]> {
  return apiFetch<IntentSlice[]>("/api/v1/reports/intents", {
    searchParams: { from_date: fromDate, to_date: toDate },
  });
}
