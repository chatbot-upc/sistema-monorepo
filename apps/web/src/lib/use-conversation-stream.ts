"use client";

import { useEffect, useRef, useState } from "react";

export type StreamEventType =
  | "hello"
  | "message.created"
  | "conversation.escalated"
  | "conversation.status_changed";

export interface StreamEvent<T = unknown> {
  type: StreamEventType;
  data: T;
  ts?: string;
}

export interface UseConversationStreamReturn {
  connected: boolean;
  lastEvent: StreamEvent | null;
}

const BACKOFF_MS = [500, 1000, 2000, 5000, 10000];

/**
 * Subscribe to the realtime CRM event stream. Lives until unmount; reconnects
 * automatically with exponential backoff. `onEvent` runs for every event so
 * callers can update React state without re-rendering on every retry.
 */
export function useConversationStream(
  user: string,
  onEvent: (event: StreamEvent) => void,
): UseConversationStreamReturn {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<StreamEvent | null>(null);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  useEffect(() => {
    let attempt = 0;
    let ws: WebSocket | null = null;
    let stopped = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const wsUrlBase = (() => {
      // NEXT_PUBLIC_API_URL is "http://localhost:8000"; flip to ws://.
      const httpBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      return httpBase.replace(/^http/, "ws");
    })();

    const connect = () => {
      if (stopped) return;
      // Plain concatenation on purpose — `encodeURIComponent` turns "@" into
      // "%40" and uvicorn's WS handshake rejects that combination with 400.
      // The user value is a known-shape email so no other chars need escaping.
      const url = `${wsUrlBase}/api/v1/ws/conversations?user=${user}`;
      ws = new WebSocket(url);
      ws.onopen = () => {
        attempt = 0;
        setConnected(true);
      };
      ws.onmessage = (e) => {
        try {
          const parsed: StreamEvent = JSON.parse(e.data);
          setLastEvent(parsed);
          callbackRef.current(parsed);
        } catch {
          // ignore malformed frames
        }
      };
      ws.onerror = () => {
        // onclose will handle the reconnect
      };
      ws.onclose = () => {
        setConnected(false);
        if (stopped) return;
        const delay = BACKOFF_MS[Math.min(attempt, BACKOFF_MS.length - 1)];
        attempt += 1;
        retryTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (ws && ws.readyState <= WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [user]);

  return { connected, lastEvent };
}
