"use server";

import {
  fetchConversationsByDay,
  fetchIntentDistribution,
  fetchReportSummary,
  type DayCount,
  type IntentSlice,
  type ReportSummary,
} from "@/lib/api/reports";

export interface ReportsData {
  summary: ReportSummary;
  daily: DayCount[];
  intents: IntentSlice[];
}

export type ReportsResult =
  | { ok: true; data: ReportsData }
  | { ok: false; error: string };

export async function fetchReportsAction(
  fromDate: string,
  toDate: string,
): Promise<ReportsResult> {
  try {
    const [summary, daily, intents] = await Promise.all([
      fetchReportSummary(fromDate, toDate),
      fetchConversationsByDay(fromDate, toDate),
      fetchIntentDistribution(fromDate, toDate),
    ]);
    return { ok: true, data: { summary, daily, intents } };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : "No se pudieron cargar los reportes.",
    };
  }
}
