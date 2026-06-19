"use server";

import { ApiError } from "@/lib/api/client";
import {
  assignTag,
  closeConversation,
  createNote,
  deleteConversation,
  deleteNote,
  fetchConversations,
  fetchHistory,
  fetchNotes,
  reopenConversation,
  releaseConversation,
  sendConversationMessage,
  setStar,
  takeoverConversation,
  unassignTag,
  updateContact,
  updateNote,
  type ConversationDetail,
  type ConversationHistory,
  type ConversationListItem,
  type InternalNote,
  type Page,
  type SendMessageResponse,
  type Tag,
} from "@/lib/api/conversations";
import { createTag, fetchTags, type TagColor } from "@/lib/api/tags";

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
  inReplyToId?: number | null,
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
    const data = await sendConversationMessage(id, trimmed, inReplyToId);
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

export async function deleteAction(id: number): Promise<ActionResult> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    await deleteConversation(id);
    return { ok: true, data: undefined };
  } catch (err) {
    return toError(err, "No se pudo eliminar la conversación.");
  }
}

// Carga una página adicional de la lista para el scroll infinito de la barra
// lateral. El componente cliente no puede llamar al API directo (apiFetch usa
// la sesión del servidor), así que pasa por aquí.
export async function loadConversationsAction(
  page: number,
  size = 20,
): Promise<ActionResult<Page<ConversationListItem>>> {
  if (!Number.isInteger(page) || page < 1) {
    return { ok: false, status: 400, error: "Página inválida." };
  }
  try {
    const data = await fetchConversations({ page, size });
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudieron cargar más conversaciones.");
  }
}

// ── Ficha de contacto ────────────────────────────────────────────────

export async function updateContactAction(
  id: number,
  email: string | null,
): Promise<ActionResult<ConversationDetail>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    const data = await updateContact(id, email);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo actualizar el correo.");
  }
}

export async function setStarAction(
  id: number,
  starred: boolean,
): Promise<ActionResult<ConversationDetail>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    const data = await setStar(id, starred);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo actualizar la conversación.");
  }
}

export async function historyAction(
  id: number,
): Promise<ActionResult<ConversationHistory>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    const data = await fetchHistory(id);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo cargar el historial.");
  }
}

// ── Notas internas ───────────────────────────────────────────────────

export async function listNotesAction(
  id: number,
): Promise<ActionResult<InternalNote[]>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    const data = await fetchNotes(id);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudieron cargar las notas.");
  }
}

export async function createNoteAction(
  id: number,
  body: string,
): Promise<ActionResult<InternalNote>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  const trimmed = body.trim();
  if (!trimmed) {
    return { ok: false, status: 400, error: "La nota no puede estar vacía." };
  }
  try {
    const data = await createNote(id, trimmed);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo crear la nota.");
  }
}

export async function updateNoteAction(
  id: number,
  noteId: number,
  body: string,
): Promise<ActionResult<InternalNote>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  const trimmed = body.trim();
  if (!trimmed) {
    return { ok: false, status: 400, error: "La nota no puede estar vacía." };
  }
  try {
    const data = await updateNote(id, noteId, trimmed);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo actualizar la nota.");
  }
}

export async function deleteNoteAction(
  id: number,
  noteId: number,
): Promise<ActionResult> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    await deleteNote(id, noteId);
    return { ok: true, data: undefined };
  } catch (err) {
    return toError(err, "No se pudo eliminar la nota.");
  }
}

// ── Etiquetas ────────────────────────────────────────────────────────

export async function listTagsAction(): Promise<ActionResult<Tag[]>> {
  try {
    const data = await fetchTags();
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudieron cargar las etiquetas.");
  }
}

export async function createTagAction(
  name: string,
  color: TagColor,
): Promise<ActionResult<Tag>> {
  const trimmed = name.trim();
  if (!trimmed) {
    return { ok: false, status: 400, error: "El nombre no puede estar vacío." };
  }
  try {
    const data = await createTag(trimmed, color);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo crear la etiqueta.");
  }
}

export async function assignTagAction(
  id: number,
  tagId: number,
): Promise<ActionResult<ConversationDetail>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    const data = await assignTag(id, tagId);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo asignar la etiqueta.");
  }
}

export async function unassignTagAction(
  id: number,
  tagId: number,
): Promise<ActionResult<ConversationDetail>> {
  const idErr = validateId(id);
  if (idErr) return idErr;
  try {
    const data = await unassignTag(id, tagId);
    return { ok: true, data };
  } catch (err) {
    return toError(err, "No se pudo quitar la etiqueta.");
  }
}
