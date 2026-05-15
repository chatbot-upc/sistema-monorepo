"use client";

import { useEffect, useRef } from "react";

import { registerFcmDeviceAction } from "@/app/(app)/_actions/devices";

import { requestFcmToken } from "./firebase";

const REGISTERED_KEY = "upcbot.fcm.registered_token";

/**
 * Request notification permission once per session and register the FCM
 * token against the backend (via Server Action so the JWT comes from the
 * Auth.js session, not from the browser).
 *
 * Mount inside the authenticated layout.
 */
export function useFcmRegister(): void {
  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;

    (async () => {
      const token = await requestFcmToken();
      if (!token) return;

      const existing = sessionStorage.getItem(REGISTERED_KEY);
      if (existing === token) return;

      const res = await registerFcmDeviceAction({
        fcm_token: token,
        platform: "web",
        user_agent: navigator.userAgent,
      });
      if (res.ok) {
        sessionStorage.setItem(REGISTERED_KEY, token);
      } else {
        console.error("[fcm] register failed", res);
      }
    })();
  }, []);
}
