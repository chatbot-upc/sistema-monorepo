import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Tag,
  Sparkles,
  BarChart3,
  Activity,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: number;
};

// Fuente única de la navegación, compartida por el Sidebar (desktop) y el
// MobileNav (drawer en móvil) para no duplicar la lista.
export const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/conversations", label: "Conversaciones", icon: MessageSquare },
  { href: "/documents", label: "Documentos", icon: FileText },
  { href: "/intents", label: "Intenciones", icon: Tag },
  { href: "/prompts", label: "Prompt", icon: Sparkles },
  { href: "/reports", label: "Reportes", icon: BarChart3 },
  { href: "/monitoring", label: "Monitoreo", icon: Activity },
];
