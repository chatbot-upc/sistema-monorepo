"use server";

import { auth } from "@/auth";

/**
 * Mint a one-shot ticket for the realtime WebSocket. Runs server-side so the
 * admin's Bearer JWT never reaches client JS — only the opaque ticket does.
 */
export async function requestWsTicket(): Promise<{
  ticket: string;
  expires_in: number;
} | null> {
  const session = await auth();
  const bearer = session?.idToken ?? session?.accessToken;
  if (!bearer) return null;

  const apiUrl =
    process.env.API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000";

  const res = await fetch(`${apiUrl}/api/v1/auth/ws-ticket`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${bearer}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as { ticket: string; expires_in: number };
}
