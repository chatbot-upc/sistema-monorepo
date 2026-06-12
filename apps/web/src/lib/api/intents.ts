import { apiFetch } from "./client";

export interface IntentRead {
  id: number;
  name: string;
  description: string | null;
  examples: string[];
  active: boolean;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface IntentCreatePayload {
  name: string;
  description?: string | null;
  examples: string[];
}

export interface IntentUpdatePayload {
  description?: string | null;
  examples?: string[];
  active?: boolean;
}

export async function fetchIntents(
  params: { active?: boolean; page?: number; size?: number } = {},
): Promise<Page<IntentRead>> {
  return apiFetch<Page<IntentRead>>("/api/v1/intents", {
    searchParams: {
      active: params.active === undefined ? undefined : String(params.active),
      page: params.page ?? 1,
      size: params.size ?? 100,
    },
  });
}

export async function createIntent(
  payload: IntentCreatePayload,
): Promise<IntentRead> {
  return apiFetch<IntentRead>("/api/v1/intents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateIntent(
  id: number,
  payload: IntentUpdatePayload,
): Promise<IntentRead> {
  return apiFetch<IntentRead>(`/api/v1/intents/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteIntent(id: number): Promise<void> {
  return apiFetch<void>(`/api/v1/intents/${id}`, { method: "DELETE" });
}
