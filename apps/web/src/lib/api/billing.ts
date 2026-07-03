import { apiFetch } from "./client";

export interface BillingOverview {
  students: number;
  installments: number;
  pending_installments: number;
  total_pending: number | string;
  currency: string;
}

export interface BillingImportResult {
  students: number;
  inserted: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export async function fetchBillingOverview(): Promise<BillingOverview> {
  return apiFetch<BillingOverview>("/api/v1/billing/overview");
}

export async function importBilling(form: FormData): Promise<BillingImportResult> {
  return apiFetch<BillingImportResult>("/api/v1/billing/import", {
    method: "POST",
    body: form,
  });
}
