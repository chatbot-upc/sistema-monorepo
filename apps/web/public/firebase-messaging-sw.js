// Firebase Cloud Messaging service worker.
// IMPORTANT: Service workers cannot read process.env. Replace these values
// with the same firebaseConfig object you put in apps/web/.env.local.
// (apiKey is safe to expose: it identifies the Firebase project, not auth.)

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
    data,
  };
  self.registration.showNotification(title, options);
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/dashboard";
  event.waitUntil(clients.openWindow(url));
});
