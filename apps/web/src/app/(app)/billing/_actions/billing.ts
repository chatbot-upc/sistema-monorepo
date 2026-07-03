"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api/client";
import {
  fetchBillingOverview,
  importBilling,
  type BillingImportResult,
  type BillingOverview,
} from "@/lib/api/billing";

export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

function detailFrom(body: string): string {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    /* body no es JSON */
  }
  return body.slice(0, 200);
}

export async function fetchBillingOverviewAction(): Promise<
  ActionResult<BillingOverview>
> {
  try {
    return { ok: true, data: await fetchBillingOverview() };
  } catch (err) {
    return {
      ok: false,
      error:
        err instanceof Error
          ? err.message
          : "No se pudo cargar el estado de facturación.",
    };
  }
}

export async function importBillingAction(
  formData: FormData,
): Promise<ActionResult<BillingImportResult>> {
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { ok: false, error: "Selecciona un archivo antes de subir." };
  }
  const upstream = new FormData();
  upstream.set("file", file);

  try {
    const result = await importBilling(upstream);
    revalidatePath("/billing");
    return { ok: true, data: result };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, error: detailFrom(err.body) || `Error ${err.status}` };
    }
    return {
      ok: false,
      error: err instanceof Error ? err.message : "Error desconocido",
    };
  }
}
