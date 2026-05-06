"use client";

import { useEffect, type RefObject } from "react";

/**
 * Scrolls the given container to its bottom whenever `key` changes
 * (typically `messages.length` or `conversationId`).
 */
export function useThreadScroll(
  ref: RefObject<HTMLElement | null>,
  key: number | string
) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}
