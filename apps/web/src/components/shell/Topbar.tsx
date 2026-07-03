"use client";

import { useState } from "react";
import { Calendar, Search } from "lucide-react";
import { NotificationsDropdown } from "./NotificationsDropdown";
import { MobileNav } from "./MobileNav";

interface TopbarProps {
  conversationsCount?: number;
}

export function Topbar({ conversationsCount }: TopbarProps) {
  const [query, setQuery] = useState("");
  const today = new Date().toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="flex items-center gap-2 sm:gap-3">
      <MobileNav conversationsCount={conversationsCount} />
      <div className="flex-1 min-w-0 relative bg-surface rounded-full pl-12 pr-5 h-11 flex items-center">
        <Search
          size={17}
          className="absolute left-5 top-1/2 -translate-y-1/2 text-muted"
          strokeWidth={1.75}
        />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="bg-transparent border-none w-full text-[13px] placeholder:text-muted focus:outline-none"
          placeholder="Buscar conversación, estudiante o documento..."
        />
      </div>

      <div className="hidden lg:flex bg-surface rounded-full px-5 h-11 items-center gap-2.5 text-[13px] text-fg-2 shrink-0">
        <Calendar size={16} className="text-muted" strokeWidth={1.75} />
        {today}
      </div>

      <NotificationsDropdown />
    </div>
  );
}
