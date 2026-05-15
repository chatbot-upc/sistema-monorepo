"use server";

import { auth } from "@/auth";

type RegisterDeviceInput = {
  fcm_token: string;
  platform?: string;
  user_agent?: string;
};

export async function registerFcmDeviceAction(
  input: RegisterDeviceInput,
): Promise<{ ok: boolean; status?: number; error?: string }> {
  const session = await auth();
  if (!session?.idToken) {
    return { ok: false, error: "no_session" };
  }

  const apiUrl = process.env.API_URL ?? "http://localhost:8000";
  const res = await fetch(`${apiUrl}/api/v1/admin/devices`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.idToken}`,
    },
    body: JSON.stringify({
      fcm_token: input.fcm_token,
      platform: input.platform ?? "web",
      user_agent: input.user_agent ?? null,
    }),
    cache: "no-store",
  });

  if (!res.ok) {
    return { ok: false, status: res.status };
  }
  return { ok: true };
}
