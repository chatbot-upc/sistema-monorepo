/**
 * Server-side fetch wrapper for the FastAPI backend.
 *
 * SW-43 uses the dev-bypass header `X-Dev-User` while Auth.js v5 lands in Fase 5.
 * Once Cognito JWT lives in the session, swap `devUser` for the real bearer.
 */

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
  const baseHeaders: Record<string, string> = { "X-Dev-User": DEV_USER };
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
