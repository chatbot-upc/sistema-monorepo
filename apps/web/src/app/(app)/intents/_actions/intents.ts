"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api/client";
import {
  createIntent,
  deleteIntent,
  updateIntent,
  type IntentCreatePayload,
  type IntentRead,
  type IntentUpdatePayload,
} from "@/lib/api/intents";

export type ActionResult<T = void> =
  | { ok: true; data: T }
  | { ok: false; status: number; error: string };

function parseDetail(body: string): string | null {
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.detail === "string") return parsed.detail;
    return null;
  } catch {
    return null;
  }
}

function toError(err: unknown, fallback: string): ActionResult<never> {
  if (err instanceof ApiError) {
    const detail = parseDetail(err.body) ?? err.body.slice(0, 200);
    return { ok: false, status: err.status, error: detail || fallback };
  }
  return {
    ok: false,
    status: 0,
    error: err instanceof Error ? err.message : fallback,
  };
}

export async function createIntentAction(
  payload: IntentCreatePayload,
): Promise<ActionResult<IntentRead>> {
  if (!/^[a-z0-9_]+$/.test(payload.name)) {
    return {
      ok: false,
      status: 400,
      error: "El nombre debe ser snake_case (a-z, 0-9, _).",
    };
  }
  if (payload.examples.length === 0) {
    return { ok: false, status: 400, error: "Agrega al menos un ejemplo." };
  }
  try {
    const data = await createIntent(payload);
    revalidatePath("/intents");
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo crear la intención.");
  }
}

export async function updateIntentAction(
  id: number,
  payload: IntentUpdatePayload,
): Promise<ActionResult<IntentRead>> {
  if (payload.examples && payload.examples.length === 0) {
    return { ok: false, status: 400, error: "Agrega al menos un ejemplo." };
  }
  try {
    const data = await updateIntent(id, payload);
    revalidatePath("/intents");
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo actualizar la intención.");
  }
}

export async function deleteIntentAction(id: number): Promise<ActionResult> {
  try {
    await deleteIntent(id);
    revalidatePath("/intents");
    return { ok: true, data: undefined };
  } catch (err) {
    return toError(err, "No se pudo eliminar la intención.");
  }
}
