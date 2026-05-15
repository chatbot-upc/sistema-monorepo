"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api/client";
import {
  deleteDocument,
  uploadDocument,
  type DocumentRead,
} from "@/lib/api/documents";

export type ActionResult<T = void> =
  | { ok: true; data: T }
  | {
      ok: false;
      status: number;
      error: string;
      code?: "duplicate" | "validation" | "not_found";
    };

export interface UploadActionData {
  id: number;
  title: string;
}

function parseDetail(body: string): string | null {
  try {
    const parsed = JSON.parse(body);
    return typeof parsed.detail === "string" ? parsed.detail : null;
  } catch {
    return null;
  }
}

export async function uploadDocumentAction(
  formData: FormData,
): Promise<ActionResult<UploadActionData>> {
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return {
      ok: false,
      status: 400,
      error: "Selecciona un archivo antes de subir.",
      code: "validation",
    };
  }

  // The backend only accepts these three values for source_type. The CRM
  // upload flow is always source_type="upload".
  const upstream = new FormData();
  upstream.set("file", file);
  upstream.set("source_type", "upload");

  try {
    const doc: DocumentRead = await uploadDocument(upstream);
    revalidatePath("/documents");
    return { ok: true, data: { id: doc.id, title: doc.title } };
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 409) {
        const detail = parseDetail(err.body) ?? "Documento duplicado";
        return {
          ok: false,
          status: 409,
          error: detail,
          code: "duplicate",
        };
      }
      const detail = parseDetail(err.body) ?? err.body.slice(0, 200);
      return { ok: false, status: err.status, error: detail || "Error inesperado" };
    }
    return {
      ok: false,
      status: 0,
      error: err instanceof Error ? err.message : "Error desconocido",
    };
  }
}

export async function deleteDocumentAction(
  id: number,
): Promise<ActionResult> {
  if (!Number.isInteger(id) || id <= 0) {
    return {
      ok: false,
      status: 400,
      error: "Identificador inválido.",
      code: "validation",
    };
  }
  try {
    await deleteDocument(id);
    revalidatePath("/documents");
    return { ok: true, data: undefined };
  } catch (err) {
    if (err instanceof ApiError) {
      const detail = parseDetail(err.body) ?? err.body.slice(0, 200);
      const code = err.status === 404 ? "not_found" : undefined;
      return {
        ok: false,
        status: err.status,
        error: detail || "No se pudo eliminar el documento.",
        code,
      };
    }
    return {
      ok: false,
      status: 0,
      error: err instanceof Error ? err.message : "Error desconocido",
    };
  }
}
