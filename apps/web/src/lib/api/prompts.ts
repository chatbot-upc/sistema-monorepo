import { apiFetch } from "./client";

export interface PromptVersion {
  id: number;
  name: string;
  version: number;
  content: string;
  active: boolean;
  created_at: string;
}

export async function fetchPromptVersions(): Promise<PromptVersion[]> {
  return apiFetch<PromptVersion[]>("/api/v1/prompts");
}

export async function createPromptVersion(
  content: string,
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>("/api/v1/prompts", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function updatePromptVersion(
  id: number,
  content: string,
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(`/api/v1/prompts/${id}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export async function activatePromptVersion(
  id: number,
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(`/api/v1/prompts/${id}/activate`, {
    method: "POST",
  });
}

export async function deletePromptVersion(id: number): Promise<void> {
  return apiFetch<void>(`/api/v1/prompts/${id}`, { method: "DELETE" });
}
