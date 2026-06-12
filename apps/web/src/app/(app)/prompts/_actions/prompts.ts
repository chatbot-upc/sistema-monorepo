"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api/client";
import {
  activatePromptVersion,
  createPromptVersion,
  deletePromptVersion,
  updatePromptVersion,
  type PromptVersion,
} from "@/lib/api/prompts";

export type ActionResult<T = void> =
  | { ok: true; data: T }
  | { ok: false; status: number; error: string };

function parseDetail(body: string): string | null {
  try {
    const parsed = JSON.parse(body);
    return typeof parsed.detail === "string" ? parsed.detail : null;
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

function validateContent(content: string): ActionResult<never> | null {
  if (content.trim().length < 20) {
    return {
      ok: false,
      status: 400,
      error: "El prompt debe tener al menos 20 caracteres.",
    };
  }
  return null;
}

export async function createPromptVersionAction(
  content: string,
): Promise<ActionResult<PromptVersion>> {
  const invalid = validateContent(content);
  if (invalid) return invalid;
  try {
    const data = await createPromptVersion(content);
    revalidatePath("/prompts");
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo crear la versión.");
  }
}

export async function updatePromptVersionAction(
  id: number,
  content: string,
): Promise<ActionResult<PromptVersion>> {
  const invalid = validateContent(content);
  if (invalid) return invalid;
  try {
    const data = await updatePromptVersion(id, content);
    revalidatePath("/prompts");
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo actualizar la versión.");
  }
}

export async function activatePromptVersionAction(
  id: number,
): Promise<ActionResult<PromptVersion>> {
  try {
    const data = await activatePromptVersion(id);
    revalidatePath("/prompts");
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo activar la versión.");
  }
}

export async function deletePromptVersionAction(
  id: number,
): Promise<ActionResult> {
  try {
    await deletePromptVersion(id);
    revalidatePath("/prompts");
    return { ok: true, data: undefined };
  } catch (err) {
    return toError(err, "No se pudo eliminar la versión.");
  }
}
