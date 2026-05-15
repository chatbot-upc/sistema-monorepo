"use client";

import { initializeApp, type FirebaseApp } from "firebase/app";
import {
  getMessaging,
  getToken,
  onMessage,
  type Messaging,
} from "firebase/messaging";

const config = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? "",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ?? "",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ?? "",
  messagingSenderId:
    process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID ?? "",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID ?? "",
};

let _app: FirebaseApp | null = null;
let _messaging: Messaging | null = null;

function isConfigured(): boolean {
  return Boolean(config.apiKey && config.projectId && config.appId);
}

function getApp(): FirebaseApp | null {
  if (typeof window === "undefined") return null;
  if (!isConfigured()) return null;
  if (_app === null) {
    _app = initializeApp(config);
  }
  return _app;
}

function getMessagingInstance(): Messaging | null {
  if (typeof window === "undefined") return null;
  const app = getApp();
  if (app === null) return null;
  if (_messaging === null) {
    _messaging = getMessaging(app);
  }
  return _messaging;
}

/**
 * Request notification permission and return FCM token. null if denied,
 * not configured, unsupported, or browser blocked.
 */
export async function requestFcmToken(): Promise<string | null> {
  const messaging = getMessagingInstance();
  if (messaging === null) return null;

  const vapidKey = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY;
  if (!vapidKey) {
    console.warn("[fcm] missing NEXT_PUBLIC_FIREBASE_VAPID_KEY");
    return null;
  }

  if (!("Notification" in window) || !("serviceWorker" in navigator)) {
    return null;
  }

  let permission = Notification.permission;
  if (permission === "default") {
    permission = await Notification.requestPermission();
  }
  if (permission !== "granted") return null;

  try {
    await navigator.serviceWorker.register("/firebase-messaging-sw.js");
    // Wait for the SW to become active (subscribe() requires an active worker)
    const reg = await navigator.serviceWorker.ready;
    const token = await getToken(messaging, {
      vapidKey,
      serviceWorkerRegistration: reg,
    });
    return token || null;
  } catch (err) {
    console.error("[fcm] getToken failed", err);
    return null;
  }
}

/**
 * Listen to foreground messages (when the app is open).
 */
export function onForegroundMessage(
  cb: (payload: {
    notification?: { title?: string; body?: string };
    data?: Record<string, string>;
  }) => void,
): () => void {
  const messaging = getMessagingInstance();
  if (messaging === null) return () => {};
  return onMessage(messaging, cb);
}
