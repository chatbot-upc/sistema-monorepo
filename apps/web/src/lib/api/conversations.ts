import { apiFetch } from "./client";

export type ConversationStatus = "abierta" | "cerrada" | "takeover";
export type MessageRole = "student" | "bot" | "admin";

export interface StudentRef {
  phone_e164: string;
  display_name: string | null;
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
}

export interface ConversationDetail {
  id: number;
  student_phone: string;
  display_name: string | null;
  status: ConversationStatus;
  opened_at: string;
  closed_at: string | null;
  takeover_admin: number | null;
  messages: MessageRead[];
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
      size: params.size ?? 50,
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
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(
    `/api/v1/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ body }),
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
