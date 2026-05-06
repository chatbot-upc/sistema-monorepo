"use client";

import { useSyncExternalStore } from "react";
import { subscribe } from "./mock";

/**
 * Suscribe el componente al store de mock y devuelve el valor seleccionado.
 * El selector debe devolver una referencia estable cuando no hay cambios
 * (las funciones `getConversations`, `getDocuments`, `getIntents`, `getThread`,
 * `getMeta` ya cumplen este contrato).
 */
export function useMockStore<T>(
  selector: () => T,
  serverSelector: () => T = selector
): T {
  return useSyncExternalStore(subscribe, selector, serverSelector);
}
