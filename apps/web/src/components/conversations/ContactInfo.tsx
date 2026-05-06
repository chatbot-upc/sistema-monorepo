"use client";

import { useState } from "react";
import { useMockStore } from "@/lib/useMockStore";
import { getConversations, getMeta } from "@/lib/mock";
import { ContactHeader } from "./contact-info/ContactHeader";
import { ContactActions } from "./contact-info/ContactActions";
import { StudentInfoSection } from "./contact-info/StudentInfoSection";
import { TagSection } from "./contact-info/TagSection";
import { NotesSection } from "./contact-info/NotesSection";
import { HistorySection } from "./contact-info/HistorySection";
import { EditContactDrawer } from "./contact-info/EditContactDrawer";

interface ContactInfoProps {
  conversationId: string;
}

export function ContactInfo({ conversationId }: ContactInfoProps) {
  const conversations = useMockStore(getConversations);
  const meta = useMockStore(() => getMeta(conversationId));
  const conversation = conversations.find((c) => c.id === conversationId);
  const [editOpen, setEditOpen] = useState(false);

  if (!conversation) return null;

  return (
    <aside className="bg-surface rounded-3xl p-6 w-[340px] shrink-0 overflow-y-auto flex flex-col gap-6">
      <ContactHeader conversation={conversation} favorite={meta.favorite} />

      <ContactActions conversation={conversation} blocked={meta.blocked} />

      <StudentInfoSection
        conversation={conversation}
        onEdit={() => setEditOpen(true)}
      />

      <TagSection conversationId={conversationId} tags={meta.tags} />

      <NotesSection conversationId={conversationId} notes={meta.notes} />

      <HistorySection />

      <EditContactDrawer
        open={editOpen}
        onOpenChange={setEditOpen}
        conversation={conversation}
      />
    </aside>
  );
}
