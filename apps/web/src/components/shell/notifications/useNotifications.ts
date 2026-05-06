"use client";

import { useMemo, useState } from "react";

export type NotifKind = "escalation" | "doc" | "system" | "message";

export interface Notif {
  id: string;
  kind: NotifKind;
  title: string;
  description: string;
  time: string;
  href: string;
  read: boolean;
}

const SEED: Notif[] = [
  {
    id: "n1",
    kind: "escalation",
    title: "Conversación escalada",
    description: "María Paula Rivera espera respuesta hace 4 min.",
    time: "09:16",
    href: "/conversations/mp-001",
    read: false,
  },
  {
    id: "n2",
    kind: "escalation",
    title: "Conversación escalada",
    description: "Juan Carlos Méndez · cargo por reincorporación.",
    time: "09:12",
    href: "/conversations/jc-002",
    read: false,
  },
  {
    id: "n3",
    kind: "doc",
    title: "Indexación completa",
    description: "matricula_2026.pdf · 142 chunks listos.",
    time: "08:45",
    href: "/documents",
    read: false,
  },
  {
    id: "n4",
    kind: "system",
    title: "Reporte semanal listo",
    description: "Reporte del 21 abr - 28 abr disponible.",
    time: "Ayer",
    href: "/reports",
    read: true,
  },
  {
    id: "n5",
    kind: "message",
    title: "Nueva conversación",
    description: "Diego Ramírez · qué requisitos necesito...",
    time: "Ayer",
    href: "/conversations/dr-005",
    read: true,
  },
];

export type NotifTab = "unread" | "all";

interface NotificationsState {
  items: Notif[];
  tab: NotifTab;
  setTab: (t: NotifTab) => void;
  unreadCount: number;
  visible: Notif[];
  markRead: (id: string) => void;
  markAllRead: () => void;
}

export function useNotifications(): NotificationsState {
  const [items, setItems] = useState<Notif[]>(SEED);
  const [tab, setTab] = useState<NotifTab>("unread");

  const unreadCount = useMemo(
    () => items.filter((n) => !n.read).length,
    [items]
  );
  const visible = useMemo(
    () => (tab === "unread" ? items.filter((n) => !n.read) : items),
    [items, tab]
  );

  const markRead = (id: string) =>
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  const markAllRead = () =>
    setItems((prev) => prev.map((n) => ({ ...n, read: true })));

  return { items, tab, setTab, unreadCount, visible, markRead, markAllRead };
}
