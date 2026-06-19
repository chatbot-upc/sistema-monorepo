import { apiFetch } from "./client";

export type ConversationStatus = "abierta" | "cerrada" | "takeover";
export type MessageRole = "student" | "bot" | "admin";

export interface StudentRef {
  phone_e164: string;
  display_name: string | null;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
}

export interface ConversationListItem {
  id: number;
  student_phone: string;
  display_name: string | null;
  status: ConversationStatus;
  opened_at: string;
  closed_at: string | null;
  message_count: number;
  last_message_preview: string | null;
  starred: boolean;
}

export interface QuotedSnapshot {
  id: number;
  role: MessageRole;
  content: string;
  created_at: string | null;
}

export interface MessageRead {
  id: number;
  conversation_id: number;
  role: MessageRole;
  content: string;
  intent_id: number | null;
  retrieved_chunks: unknown[];
  input_tokens: number | null;
  output_tokens: number | null;
  model_used: string | null;
  latency_ms: number | null;
  meta_message_id: string | null;
  created_at: string;
  in_reply_to_id: number | null;
  quoted: QuotedSnapshot | null;
  delivery_status: DeliveryStatus | null;
}

export type DeliveryStatus = "sent" | "delivered" | "read" | "failed";

export interface StudentProfile {
  phone_e164: string;
  full_name: string;
  career: string | null;
  cycle: number | null;
  campus: string | null;
  modality: string | null;
  academic_status: string | null;
  failed_courses: string | null;
  enrollment_turn: string | null;
  english_level: number | null;
  elective_credits: number | null;
  internship_credits: number | null;
}

export interface ConversationDetail {
  id: number;
  student_phone: string;
  display_name: string | null;
  email: string | null;
  status: ConversationStatus;
  opened_at: string;
  closed_at: string | null;
  takeover_admin: number | null;
  starred: boolean;
  student_profile: StudentProfile | null;
  tags: Tag[];
  messages: MessageRead[];
}

export interface InternalNote {
  id: number;
  body: string;
  author_admin_id: number | null;
  author_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationHistory {
  total_conversations: number;
  total_messages: number;
  first_contact: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface FetchConversationsParams {
  status?: ConversationStatus;
  phone?: string;
  page?: number;
  size?: number;
}

export async function fetchConversations(
  params: FetchConversationsParams = {},
): Promise<Page<ConversationListItem>> {
  return apiFetch<Page<ConversationListItem>>("/api/v1/conversations", {
    searchParams: {
      status: params.status,
      phone: params.phone,
      page: params.page ?? 1,
      size: params.size ?? 20,
    },
  });
}

export async function fetchConversation(
  id: number,
): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(`/api/v1/conversations/${id}`);
}

export async function fetchMessages(
  conversationId: number,
  params: { page?: number; size?: number } = {},
): Promise<Page<MessageRead>> {
  return apiFetch<Page<MessageRead>>(
    `/api/v1/conversations/${conversationId}/messages`,
    {
      searchParams: {
        page: params.page ?? 1,
        size: params.size ?? 100,
      },
    },
  );
}

export interface SendMessageResponse {
  message_id: number;
  meta_message_id: string | null;
  conversation_status: ConversationStatus;
}

export async function sendConversationMessage(
  conversationId: number,
  body: string,
  inReplyToId?: number | null,
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(
    `/api/v1/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ body, in_reply_to_id: inReplyToId ?? null }),
    },
  );
}

export async function takeoverConversation(
  conversationId: number,
): Promise<unknown> {
  return apiFetch<unknown>(`/api/v1/conversations/${conversationId}/takeover`, {
    method: "POST",
  });
}

export async function releaseConversation(
  conversationId: number,
): Promise<unknown> {
  return apiFetch<unknown>(`/api/v1/conversations/${conversationId}/release`, {
    method: "POST",
  });
}

export async function closeConversation(
  conversationId: number,
): Promise<unknown> {
  return apiFetch<unknown>(`/api/v1/conversations/${conversationId}/close`, {
    method: "POST",
  });
}

export async function reopenConversation(
  conversationId: number,
): Promise<unknown> {
  return apiFetch<unknown>(`/api/v1/conversations/${conversationId}/reopen`, {
    method: "POST",
  });
}

export async function deleteConversation(
  conversationId: number,
): Promise<void> {
  return apiFetch<void>(`/api/v1/conversations/${conversationId}`, {
    method: "DELETE",
  });
}

// ── Ficha de contacto ────────────────────────────────────────────────

export async function updateContact(
  conversationId: number,
  email: string | null,
): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(
    `/api/v1/conversations/${conversationId}/contact`,
    { method: "PATCH", body: JSON.stringify({ email }) },
  );
}

export async function setStar(
  conversationId: number,
  starred: boolean,
): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(
    `/api/v1/conversations/${conversationId}/star`,
    { method: "PUT", body: JSON.stringify({ starred }) },
  );
}

export async function fetchHistory(
  conversationId: number,
): Promise<ConversationHistory> {
  return apiFetch<ConversationHistory>(
    `/api/v1/conversations/${conversationId}/history`,
  );
}

// ── Notas internas ───────────────────────────────────────────────────

export async function fetchNotes(
  conversationId: number,
): Promise<InternalNote[]> {
  return apiFetch<InternalNote[]>(
    `/api/v1/conversations/${conversationId}/notes`,
  );
}

export async function createNote(
  conversationId: number,
  body: string,
): Promise<InternalNote> {
  return apiFetch<InternalNote>(
    `/api/v1/conversations/${conversationId}/notes`,
    { method: "POST", body: JSON.stringify({ body }) },
  );
}

export async function updateNote(
  conversationId: number,
  noteId: number,
  body: string,
): Promise<InternalNote> {
  return apiFetch<InternalNote>(
    `/api/v1/conversations/${conversationId}/notes/${noteId}`,
    { method: "PATCH", body: JSON.stringify({ body }) },
  );
}

export async function deleteNote(
  conversationId: number,
  noteId: number,
): Promise<void> {
  return apiFetch<void>(
    `/api/v1/conversations/${conversationId}/notes/${noteId}`,
    { method: "DELETE" },
  );
}

// ── Etiquetas de la conversación ─────────────────────────────────────

export async function assignTag(
  conversationId: number,
  tagId: number,
): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(
    `/api/v1/conversations/${conversationId}/tags`,
    { method: "POST", body: JSON.stringify({ tag_id: tagId }) },
  );
}

export async function unassignTag(
  conversationId: number,
  tagId: number,
): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(
    `/api/v1/conversations/${conversationId}/tags/${tagId}`,
    { method: "DELETE" },
  );
}
