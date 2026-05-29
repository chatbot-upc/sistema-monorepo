// Firebase Cloud Messaging service worker.
// IMPORTANT: Service workers cannot read process.env. Replace these values
// with the same firebaseConfig object you put in apps/web/.env.local.
// (apiKey is safe to expose: it identifies the Firebase project, not auth.)
//
// SW version: 2 — bump this comment whenever you change the SW so the
// browser fetches the new file (it byte-compares the script body).

// Activate the new SW immediately and take control of all open clients.
// Safe here because this SW only handles FCM (no asset caching); changes
// can't cause UI/SW version mismatch.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

importScripts("https://www.gstatic.com/firebasejs/10.13.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.13.0/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyDOoXeKUZb2Si5_QeqZB-86dqaUZzJHnDo",
  authDomain: "tesis-upc-93e93.firebaseapp.com",
  projectId: "tesis-upc-93e93",
  messagingSenderId: "553117507350",
  appId: "1:553117507350:web:a061d4a78c22e48ba1ba37",
});

const messaging = firebase.messaging();

// Backend sends data-only payloads (no `notification` field) to avoid
// duplicate notifs (FCM auto + SW). Read everything from payload.data.
messaging.onBackgroundMessage((payload) => {
  const data = payload.data || {};
  const title = data.title || "UPCBot";
  const options = {
    body: data.body || "",
    icon: "/favicon.ico",
    badge: "/favicon.ico",
    // tag de-dupes notifications for the same conversation: a follow-up
    // escalation/message replaces the previous bubble instead of stacking.
    tag: data.conversation_id ? `conv-${data.conversation_id}` : undefined,
    data,
  };
  self.registration.showNotification(title, options);
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/conversations";

  event.waitUntil(
    (async () => {
      const allClients = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });

      // If a CRM tab is already open, focus it and navigate via postMessage
      // instead of opening yet another tab. Falls back to openWindow.
      for (const client of allClients) {
        const url = new URL(client.url);
        if (url.origin === self.location.origin) {
          await client.focus();
          // Try Next.js client navigation first; if no listener, fall back to
          // a full nav so the admin still lands on the right page.
          try {
            client.postMessage({ type: "fcm:navigate", url: targetUrl });
          } catch {}
          // Belt and suspenders: ensure we land on the right URL.
          if (!url.pathname.endsWith(targetUrl)) {
            return client.navigate(targetUrl).catch(() => undefined);
          }
          return;
        }
      }

      await self.clients.openWindow(targetUrl);
    })(),
  );
});
