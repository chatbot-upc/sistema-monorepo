"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Menu, X, ChevronUp, User, LogOut } from "lucide-react";
import { cn } from "@/lib/cn";
import { Avatar } from "@/components/ui/Avatar";
import { Dropdown } from "@/components/ui/Dropdown";
import { useToast } from "@/components/ui/ToastProvider";
import { lockBodyScroll } from "@/lib/scroll-lock";
import { NAV } from "./nav";

interface MobileNavProps {
  conversationsCount?: number;
}

// Navegación para móvil: botón hamburguesa (visible solo <md) + drawer lateral
// que reutiliza la misma lista NAV que el Sidebar de desktop. El Sidebar normal
// está oculto con `hidden md:flex`, así que esta es la única forma de navegar
// en pantallas estrechas.
export function MobileNav({ conversationsCount }: MobileNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);

  // Cierra el drawer al cambiar de ruta (tras navegar a una sección).
  // Sincroniza con el router (sistema externo); el lint pide suprimirlo.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOpen(false);
  }, [pathname]);

  // Bloquea el scroll del body mientras el drawer está abierto.
  useEffect(() => {
    if (!open) return;
    return lockBodyScroll();
  }, [open]);

  // Cierra con Escape.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Abrir menú"
        aria-expanded={open}
        className="md:hidden shrink-0 w-11 h-11 rounded-full bg-surface flex items-center justify-center text-fg-2 hover:text-fg transition-colors cursor-pointer"
      >
        <Menu size={18} strokeWidth={1.75} />
      </button>

      {/* Overlay + drawer. Siempre montado para animar entrada/salida con
          transiciones; pointer-events se desactiva cuando está cerrado. */}
      <div
        className={cn(
          "md:hidden fixed inset-0 z-overlay transition-opacity duration-200",
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        aria-hidden={!open}
      >
        <div
          className="absolute inset-0 bg-ink/40 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
        <aside
          className={cn(
            "absolute left-0 top-0 h-full w-[280px] max-w-[85vw] bg-surface rounded-r-3xl flex flex-col gap-1 px-4 py-6 shadow-modal transition-transform duration-200",
            open ? "translate-x-0" : "-translate-x-full"
          )}
          role="dialog"
          aria-modal="true"
        >
          {/* Brand + cerrar */}
          <div className="flex items-center justify-between px-3 pt-1 pb-6">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-primary text-white flex items-center justify-center relative font-extrabold text-sm">
                <span className="absolute w-3 h-0.5 bg-white rounded-sm" />
                <span className="absolute w-0.5 h-3 bg-white rounded-sm" />
              </div>
              <div className="font-bold text-lg tracking-[-0.3px]">
                UPC<span className="text-primary">Bot</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Cerrar menú"
              className="w-9 h-9 rounded-full flex items-center justify-center text-muted hover:text-fg hover:bg-bg-2 transition-colors cursor-pointer"
            >
              <X size={18} strokeWidth={2} />
            </button>
          </div>

          {/* Nav */}
          {NAV.map((item) => {
            const Icon = item.icon;
            const href = item.href.split("?")[0];
            const isActive =
              pathname === href || pathname.startsWith(`${href}/`);
            const badge =
              item.href === "/conversations" ? conversationsCount : item.badge;
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-[14px] transition-all relative",
                  isActive
                    ? "bg-bg-2 text-fg font-semibold"
                    : "text-muted hover:bg-bg-2 hover:text-fg-2 font-medium"
                )}
              >
                <Icon size={18} strokeWidth={1.75} className="shrink-0" />
                {item.label}
                {badge != null && badge > 0 && (
                  <span className="ml-auto bg-primary text-white font-mono text-[10px] px-2 py-0.5 rounded-full font-medium">
                    {badge}
                  </span>
                )}
              </Link>
            );
          })}

          <div className="flex-1" />

          {/* User block */}
          <div className="border-t border-line">
            <Dropdown align="start" side="top">
              <Dropdown.Trigger>
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-3 py-4 rounded-xl hover:bg-bg-2 transition-colors cursor-pointer text-left"
                >
                  <Avatar initials="RL" gradient="coral" />
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-semibold">Renzo Lenes</div>
                    <div className="text-[11px] text-muted font-mono">
                      ID: 72630284
                    </div>
                  </div>
                  <ChevronUp
                    size={14}
                    className="text-muted shrink-0"
                    strokeWidth={2}
                  />
                </button>
              </Dropdown.Trigger>
              <Dropdown.Content minWidth={228}>
                <Dropdown.Label>Cuenta</Dropdown.Label>
                <Dropdown.Item
                  icon={<User size={14} strokeWidth={2} />}
                  onSelect={() => toast.info("Mi perfil — próximamente")}
                >
                  Mi perfil
                </Dropdown.Item>
                <Dropdown.Separator />
                <Dropdown.Item
                  destructive
                  icon={<LogOut size={14} strokeWidth={2} />}
                  onSelect={() => {
                    toast.success("Sesión cerrada");
                    router.push("/login");
                  }}
                >
                  Cerrar sesión
                </Dropdown.Item>
              </Dropdown.Content>
            </Dropdown>
          </div>
        </aside>
      </div>
    </>
  );
}
