import { apiFetch } from "./client";

export type DocumentSourceType = "upload" | "scraped" | "link";
export type DocumentStatus = "pending" | "indexing" | "indexed" | "error";

export interface DocumentRead {
  id: number;
  title: string;
  program: string | null;
  source_type: DocumentSourceType;
  source_url: string | null;
  s3_key: string;
  sha256: string;
  version: number;
  status: DocumentStatus;
  error_message: string | null;
  indexed_at: string | null;
  created_at: string;
  chunk_count: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface FetchDocumentsParams {
  status?: DocumentStatus;
  source_type?: DocumentSourceType;
  page?: number;
  size?: number;
}

export async function fetchDocuments(
  params: FetchDocumentsParams = {},
): Promise<Page<DocumentRead>> {
  return apiFetch<Page<DocumentRead>>("/api/v1/documents", {
    searchParams: {
      status: params.status,
      source_type: params.source_type,
      page: params.page ?? 1,
      size: params.size ?? 100,
    },
  });
}

export interface DocumentSummary {
  total: number;
  total_chunks: number;
  indexed: number;
  indexing: number;
  pending: number;
  error: number;
}

export async function fetchDocumentsSummary(): Promise<DocumentSummary> {
  return apiFetch<DocumentSummary>("/api/v1/documents/summary");
}

export async function uploadDocument(form: FormData): Promise<DocumentRead> {
  return apiFetch<DocumentRead>("/api/v1/documents", {
    method: "POST",
    body: form,
  });
}

export interface ProgramOption {
  value: string;
  label: string;
}

export async function fetchProgramOptions(): Promise<ProgramOption[]> {
  return apiFetch<ProgramOption[]>("/api/v1/documents/programs");
}

export async function deleteDocument(id: number): Promise<void> {
  return apiFetch<void>(`/api/v1/documents/${id}`, { method: "DELETE" });
}
