"use server";

import { ApiError } from "@/lib/api/client";
import {
  closeConversation,
  reopenConversation,
  releaseConversation,
  sendConversationMessage,
  takeoverConversation,
  type SendMessageResponse,
} from "@/lib/api/conversations";

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

function validateId(id: number): ActionResult<never> | null {
  if (!Number.isInteger(id) || id <= 0) {
    return { ok: false, status: 400, error: "Identificador inválido." };
  }
  return null;
}

export async function sendMessageAction(
  id: number,
  body: string,
): Promise<ActionResult<SendMessageResponse>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  const trimmed = body.trim();
  if (!trimmed) {
    return { ok: false, status: 400, error: "El mensaje no puede estar vacío." };
  }
  if (trimmed.length > 4096) {
    return { ok: false, status: 400, error: "Máximo 4096 caracteres." };
  }
  try {
    const data = await sendConversationMessage(id, trimmed);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo enviar el mensaje.");
  }
}

export async function takeoverAction(id: number): Promise<ActionResult> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    await takeoverConversation(id);
    return { ok: true, data: undefined };
  } catch (err) {
    return toError(err, "No se pudo tomar la conversación.");
  }
}

export async function releaseAction(id: number): Promise<ActionResult> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    await releaseConversation(id);
    return { ok: true, data: undefined };
  } catch (err) {
    return toError(err, "No se pudo liberar la conversación.");
  }
}

export async function closeAction(id: number): Promise<ActionResult> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    await closeConversation(id);
    return { ok: true, data: undefined };
  } catch (err) {
    return toError(err, "No se pudo cerrar la conversación.");
  }
}

export async function reopenAction(id: number): Promise<ActionResult> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    await reopenConversation(id);
    return { ok: true, data: undefined };
  } catch (err) {
    return toError(err, "No se pudo reabrir la conversación.");
  }
}
