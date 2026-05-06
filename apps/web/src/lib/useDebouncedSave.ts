"use client";

import { useEffect, useRef } from "react";

/**
 * Auto-saves `value` calling `save(key, value)` after `delayMs` of inactivity.
 *
 * If `key` changes mid-debounce (e.g. user navigates to another conversation),
 * the pending timer is cancelled WITHOUT firing — preventing cross-key writes.
 * The "last saved" reference is rebound to the new key so the next genuine change
 * triggers a save under the right context.
 */
export function useDebouncedSave<K, V>(
  key: K,
  value: V,
  save: (key: K, value: V) => void,
  delayMs: number = 800
): void {
  const lastSaved = useRef<{ key: K; value: V }>({ key, value });
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (lastSaved.current.key !== key) {
      if (timerRef.current) clearTimeout(timerRef.current);
      lastSaved.current = { key, value };
      return;
    }
    if (Object.is(lastSaved.current.value, value)) return;

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      save(key, value);
      lastSaved.current = { key, value };
      timerRef.current = null;
    }, delayMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [key, value, save, delayMs]);
}
