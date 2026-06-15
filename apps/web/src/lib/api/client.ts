/**
 * Server-side fetch wrapper for the FastAPI backend.
 *
 * Auth: usa el JWT (id_token de Cognito) de la sesión Auth.js → `Authorization:
 * Bearer`. Si no hay sesión (dev local sin login), cae al header de bypass
 * `X-Dev-User`, que la API solo acepta con ENV=local.
 */
import { auth } from "@/auth";

const DEV_USER = "dev@upc.edu.pe";

function getBaseUrl(): string {
  const url = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!url) {
    throw new Error("API_URL or NEXT_PUBLIC_API_URL must be set");
  }
  return url.replace(/\/$/, "");
}

export interface ApiRequest extends Omit<RequestInit, "headers"> {
  searchParams?: Record<string, string | number | undefined | null>;
  headers?: Record<string, string>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly path: string,
    public readonly body: string,
  ) {
    super(`API ${status} ${path}: ${body.slice(0, 200)}`);
  }
}

export async function apiFetch<T>(path: string, init: ApiRequest = {}): Promise<T> {
  const { searchParams, headers, ...rest } = init;
  const url = new URL(`${getBaseUrl()}${path}`);
  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }

  // When body is FormData the runtime must set Content-Type with its boundary;
  // hard-coding application/json would break multipart uploads (SW-21).
  const isFormData =
    typeof FormData !== "undefined" && rest.body instanceof FormData;
  const baseHeaders: Record<string, string> = {};
  const session = await auth();
  if (session?.idToken) {
    baseHeaders["Authorization"] = `Bearer ${session.idToken}`;
  } else {
    // Fallback dev: la API solo acepta X-Dev-User con ENV=local.
    baseHeaders["X-Dev-User"] = DEV_USER;
  }
  if (!isFormData) {
    baseHeaders["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...rest,
    headers: { ...baseHeaders, ...headers },
    cache: rest.cache ?? "no-store",
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, path, body);
  }
  // 204 No Content (e.g. DELETE /documents/{id}) has no body to parse.
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as T;
  }
  return (await response.json()) as T;
}
