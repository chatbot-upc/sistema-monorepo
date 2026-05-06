"use client";

import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { useMockStore } from "@/lib/useMockStore";
import { getConversations } from "@/lib/mock";
import { useConvListFilter } from "./conv-list/useConvListFilter";
import { FilterTabs } from "./conv-list/FilterTabs";
import { ConvListItem } from "./conv-list/ConvListItem";
import { NewConversationModal } from "./conv-list/NewConversationModal";

interface ConvListProps {
  activeId: string;
}

export function ConvList({ activeId }: ConvListProps) {
  const items = useMockStore(getConversations);
  const { filter, search, setSearch, filtered, counts, buildHref } =
    useConvListFilter(items, activeId);
  const [open, setOpen] = useState(false);

  return (
    <aside className="bg-surface rounded-3xl p-5 flex flex-col gap-3.5 w-[340px] shrink-0 overflow-hidden">
      <div className="flex justify-between items-center">
        <h3 className="text-[18px] font-semibold tracking-[-0.2px]">Mensajes</h3>
        <IconButton
          variant="dark"
          size="sm"
          onClick={() => setOpen(true)}
          aria-label="Nueva conversación"
        >
          <Plus size={14} strokeWidth={2.5} />
        </IconButton>
      </div>

      <div className="bg-surface-2 rounded-full px-4 py-2.5 pl-11 relative">
        <Search
          size={16}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-muted"
          strokeWidth={2}
        />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-transparent border-none w-full text-[13px] focus:outline-none placeholder:text-muted-2"
          placeholder="Buscar por nombre o teléfono..."
        />
      </div>

      <FilterTabs filter={filter} counts={counts} buildHref={buildHref} />

      <div className="flex flex-col gap-1 overflow-y-auto flex-1 -mr-2.5 pr-2.5">
        {filtered.length === 0 && (
          <div className="text-center py-12 text-sm text-muted">
            {search
              ? "Sin resultados para tu búsqueda."
              : "Sin conversaciones en este filtro."}
          </div>
        )}
        {filtered.map((c) => (
          <ConvListItem
            key={c.id}
            conv={c}
            active={c.id === activeId}
            filter={filter}
          />
        ))}
      </div>

      <NewConversationModal open={open} onOpenChange={setOpen} />
    </aside>
  );
}
