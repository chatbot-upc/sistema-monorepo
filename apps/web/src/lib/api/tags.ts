import { apiFetch } from "./client";
import type { Tag } from "./conversations";

export type TagColor =
  | "blue"
  | "violet"
  | "amber"
  | "mint"
  | "coral"
  | "slate";

export async function fetchTags(): Promise<Tag[]> {
  return apiFetch<Tag[]>("/api/v1/tags");
}

export async function createTag(
  name: string,
  color: TagColor,
): Promise<Tag> {
  return apiFetch<Tag>("/api/v1/tags", {
    method: "POST",
    body: JSON.stringify({ name, color }),
  });
}
