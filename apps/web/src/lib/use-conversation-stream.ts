/* eslint-disable react-hooks/refs */
"use client";

import { useEffect, useRef, useState } from "react";

export type StreamEventType =
  | "hello"
  | "message.created"
  | "conversation.escalated"
  | "conversation.status_changed"
  | "conversation.deleted"
  | "document.status_changed";

export interface StreamEvent<T = unknown> {
  type: StreamEventType;
  data: T;
  ts?: string;
}

export interface UseConversationStreamReturn {
  connected: boolean;
  lastEvent: StreamEvent | null;
}

type TicketFetcher = () => Promise<{ ticket: string } | null>;

const BACKOFF_MS = [500, 1000, 2000, 5000, 10000];

/**
 * Subscribe to the realtime CRM event stream. Lives until unmount; reconnects
 * automatically with exponential backoff. `onEvent` runs for every event so
 * callers can update React state without re-rendering on every retry.
 *
 * Auth flow:
 *   1. We call `fetchTicket()` (a Server Action) which reads the admin's
 *      Cognito JWT from the Auth.js session and asks the API for a short-lived
 *      opaque ticket.
 *   2. The ticket goes on the WS query string. Tickets are one-shot (server
 *      deletes on first use) so they can't be replayed.
 *   3. On reconnect we ask for a fresh ticket — the old one is already gone.
 */
export function useConversationStream(
  fetchTicket: TicketFetcher,
  onEvent: (event: StreamEvent) => void,
): UseConversationStreamReturn {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<StreamEvent | null>(null);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;
  const ticketRef = useRef<TicketFetcher>(fetchTicket);
  ticketRef.current = fetchTicket;

  useEffect(() => {
    let attempt = 0;
    let ws: WebSocket | null = null;
    let stopped = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const wsUrlBase = (() => {
      const httpBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      return httpBase.replace(/^http/, "ws");
    })();

    const scheduleRetry = () => {
      if (stopped) return;
      const delay = BACKOFF_MS[Math.min(attempt, BACKOFF_MS.length - 1)];
      attempt += 1;
      retryTimer = setTimeout(connect, delay);
    };

    const connect = async () => {
      if (stopped) return;
      let ticketPayload: { ticket: string } | null = null;
      try {
        ticketPayload = await ticketRef.current();
      } catch {
        ticketPayload = null;
      }
      if (!ticketPayload?.ticket || stopped) {
        scheduleRetry();
        return;
      }

      const url = `${wsUrlBase}/api/v1/ws/conversations?ticket=${ticketPayload.ticket}`;
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
        scheduleRetry();
      };
    };

    void connect();

    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (ws && ws.readyState <= WebSocket.OPEN) {
        ws.close();
      }
    };
  }, []);

  return { connected, lastEvent };
}
