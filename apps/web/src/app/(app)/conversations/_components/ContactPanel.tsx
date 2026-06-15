"use client";

import { useEffect, useState, useTransition } from "react";
import {
  Check,
  Mail,
  Pencil,
  Plus,
  Star,
  Trash2,
  X,
} from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { useToast } from "@/components/ui/ToastProvider";
import { cn } from "@/lib/cn";
import { parseApiDate } from "@/lib/dates";
import type {
  ConversationDetail,
  ConversationHistory,
  InternalNote,
  Tag,
} from "@/lib/api/conversations";
import type { TagColor } from "@/lib/api/tags";
import {
  assignTagAction,
  createNoteAction,
  createTagAction,
  deleteNoteAction,
  historyAction,
  listNotesAction,
  listTagsAction,
  setStarAction,
  unassignTagAction,
  updateContactAction,
  updateNoteAction,
} from "../_actions/conversations";

const GRADIENTS = ["coral", "blue", "violet", "mint", "amber", "rose"] as const;

function gradientOf(id: number): (typeof GRADIENTS)[number] {
  return GRADIENTS[id % GRADIENTS.length];
}

function initialsOf(name: string | null, phone: string): string {
  const src = name?.trim();
  if (src) {
    const parts = src.split(/\s+/);
    return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
  }
  return phone.replace(/\D/g, "").slice(-2);
}

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  return parseApiDate(iso).toLocaleDateString("es-PE", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

function fmtDateTime(iso: string): string {
  return parseApiDate(iso).toLocaleString("es-PE", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const TAG_STYLES: Record<string, string> = {
  blue: "bg-blue-soft text-blue",
  violet: "bg-violet-soft text-violet",
  amber: "bg-amber-soft text-amber-fg",
  mint: "bg-mint-soft text-success",
  coral: "bg-coral-soft text-coral",
  slate: "bg-surface-2 text-muted",
};

const TAG_SWATCHES: Record<TagColor, string> = {
  blue: "bg-blue",
  violet: "bg-violet",
  amber: "bg-amber",
  mint: "bg-mint",
  coral: "bg-coral",
  slate: "bg-muted-2",
};

const COLOR_KEYS = Object.keys(TAG_SWATCHES) as TagColor[];

interface Props {
  conversation: ConversationDetail;
  onChange: (c: ConversationDetail) => void;
}

export function ContactPanel({ conversation, onChange }: Props) {
  const { toast } = useToast();
  const id = conversation.id;
  const profile = conversation.student_profile;
  const name = profile?.full_name ?? conversation.display_name ?? conversation.student_phone;

  const [history, setHistory] = useState<ConversationHistory | null>(null);
  const [notes, setNotes] = useState<InternalNote[]>([]);
  const [catalog, setCatalog] = useState<Tag[]>([]);
  const [pending, start] = useTransition();

  // Carga inicial por conversación (el panel se remonta al cambiar de chat).
  useEffect(() => {
    let alive = true;
    void (async () => {
      const [h, n, t] = await Promise.all([
        historyAction(id),
        listNotesAction(id),
        listTagsAction(),
      ]);
      if (!alive) return;
      if (h.ok) setHistory(h.data);
      if (n.ok) setNotes(n.data);
      if (t.ok) setCatalog(t.data);
    })();
    return () => {
      alive = false;
    };
  }, [id]);

  const toggleStar = () => {
    start(async () => {
      const r = await setStarAction(id, !conversation.starred);
      if (r.ok) onChange(r.data);
      else toast.error("No se pudo actualizar", { description: r.error });
    });
  };

  return (
    <aside className="w-[300px] shrink-0 min-h-0">
      <div className="bg-surface rounded-3xl h-full overflow-auto">
        {/* Cabecera */}
        <div className="p-6 flex flex-col items-center text-center border-b border-line relative">
          <button
            type="button"
            onClick={toggleStar}
            disabled={pending}
            aria-label={conversation.starred ? "Quitar destacado" : "Destacar"}
            title={conversation.starred ? "Quitar destacado" : "Destacar"}
            className={cn(
              "absolute right-4 top-4 w-9 h-9 rounded-full flex items-center justify-center transition-colors",
              conversation.starred
                ? "bg-amber-soft text-amber"
                : "bg-surface-2 text-muted hover:text-amber",
            )}
          >
            <Star
              size={16}
              strokeWidth={2}
              fill={conversation.starred ? "currentColor" : "none"}
            />
          </button>
          <Avatar
            initials={initialsOf(
              profile?.full_name ?? conversation.display_name,
              conversation.student_phone,
            )}
            gradient={gradientOf(id)}
            size="xl"
          />
          <div className="mt-3 text-[18px] font-bold tracking-[-0.4px]">{name}</div>
          <div className="text-[12px] text-muted font-mono mt-0.5">
            {conversation.student_phone}
          </div>
        </div>

        {/* Correo editable */}
        <section className="px-6 py-5 border-b border-line">
          <SectionLabel>Contacto</SectionLabel>
          <EmailField
            id={id}
            email={conversation.email}
            onChange={onChange}
          />
        </section>

        {/* Información académica */}
        <section className="px-6 py-5 border-b border-line">
          <SectionLabel>Información académica</SectionLabel>
          {profile ? (
            <div className="mt-3 flex flex-col gap-2.5">
              {profile.career && <Row label="Carrera" value={profile.career} />}
              {profile.cycle != null && (
                <Row label="Ciclo" value={`${profile.cycle}° ciclo`} />
              )}
              {profile.campus && <Row label="Campus" value={profile.campus} />}
              {profile.modality && <Row label="Modalidad" value={profile.modality} />}
              {profile.academic_status && (
                <Row label="Estado" value={profile.academic_status} />
              )}
            </div>
          ) : (
            <p className="mt-3 text-[12px] text-muted">
              Sin perfil académico vinculado a este número.
            </p>
          )}
        </section>

        {/* Etiquetas */}
        <section className="px-6 py-5 border-b border-line">
          <SectionLabel>Etiquetas</SectionLabel>
          <TagsEditor
            id={id}
            tags={conversation.tags}
            catalog={catalog}
            onCatalogChange={setCatalog}
            onChange={onChange}
          />
        </section>

        {/* Notas internas */}
        <section className="px-6 py-5 border-b border-line">
          <SectionLabel>Notas internas</SectionLabel>
          <NotesManager id={id} notes={notes} onNotesChange={setNotes} />
        </section>

        {/* Historial */}
        <section className="px-6 py-5">
          <SectionLabel>Historial</SectionLabel>
          <div className="mt-3 flex flex-col gap-2.5">
            <HistoryRow
              dot="bg-success"
              label={`${history?.total_conversations ?? "—"} conversaciones`}
              meta="totales"
            />
            <HistoryRow
              dot="bg-blue"
              label={`${history?.total_messages ?? "—"} mensajes`}
              meta="totales"
            />
            {history?.first_contact && (
              <HistoryRow
                dot="bg-muted-2"
                label="Primer contacto"
                meta={fmtDate(history.first_contact)}
              />
            )}
          </div>
        </section>
      </div>
    </aside>
  );
}

// ── Correo ──────────────────────────────────────────────────────────

function EmailField({
  id,
  email,
  onChange,
}: {
  id: number;
  email: string | null;
  onChange: (c: ConversationDetail) => void;
}) {
  const { toast } = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(email ?? "");
  const [pending, start] = useTransition();

  const save = () => {
    start(async () => {
      const r = await updateContactAction(id, draft.trim() || null);
      if (r.ok) {
        onChange(r.data);
        setEditing(false);
      } else {
        toast.error("No se pudo guardar", { description: r.error });
      }
    });
  };

  if (editing) {
    return (
      <div className="mt-3 flex items-center gap-2">
        <input
          autoFocus
          type="email"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="correo@ejemplo.com"
          className="flex-1 min-w-0 rounded-lg bg-surface-2 border border-line px-2.5 py-1.5 text-[13px] focus-visible:border-primary"
        />
        <button
          type="button"
          onClick={save}
          disabled={pending}
          aria-label="Guardar"
          className="w-8 h-8 shrink-0 rounded-lg bg-primary text-white flex items-center justify-center hover:bg-primary-hover disabled:opacity-50"
        >
          <Check size={15} strokeWidth={2.5} />
        </button>
        <button
          type="button"
          onClick={() => {
            setDraft(email ?? "");
            setEditing(false);
          }}
          aria-label="Cancelar"
          className="w-8 h-8 shrink-0 rounded-lg bg-surface-2 text-muted flex items-center justify-center hover:text-fg"
        >
          <X size={15} strokeWidth={2.5} />
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className="mt-3 w-full flex items-center gap-2.5 group text-left"
    >
      <Mail size={15} strokeWidth={2} className="text-muted shrink-0" />
      <span
        className={cn(
          "flex-1 min-w-0 truncate text-[13px]",
          email ? "text-fg" : "text-muted",
        )}
      >
        {email ?? "Agregar correo"}
      </span>
      <Pencil
        size={13}
        strokeWidth={2}
        className="text-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
      />
    </button>
  );
}

// ── Etiquetas ───────────────────────────────────────────────────────

function TagsEditor({
  id,
  tags,
  catalog,
  onCatalogChange,
  onChange,
}: {
  id: number;
  tags: Tag[];
  catalog: Tag[];
  onCatalogChange: (t: Tag[]) => void;
  onChange: (c: ConversationDetail) => void;
}) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState<TagColor>("blue");
  const [pending, start] = useTransition();

  const assignedIds = new Set(tags.map((t) => t.id));
  const available = catalog.filter((t) => !assignedIds.has(t.id));

  const assign = (tagId: number) => {
    start(async () => {
      const r = await assignTagAction(id, tagId);
      if (r.ok) onChange(r.data);
      else toast.error("No se pudo asignar", { description: r.error });
    });
  };

  const unassign = (tagId: number) => {
    start(async () => {
      const r = await unassignTagAction(id, tagId);
      if (r.ok) onChange(r.data);
      else toast.error("No se pudo quitar", { description: r.error });
    });
  };

  const createAndAssign = () => {
    const name = newName.trim();
    if (!name) return;
    start(async () => {
      const created = await createTagAction(name, newColor);
      if (!created.ok) {
        toast.error("No se pudo crear", { description: created.error });
        return;
      }
      onCatalogChange([...catalog, created.data].sort((a, b) => a.name.localeCompare(b.name)));
      const assigned = await assignTagAction(id, created.data.id);
      if (assigned.ok) {
        onChange(assigned.data);
        setNewName("");
      } else {
        toast.error("Etiqueta creada pero no asignada", {
          description: assigned.error,
        });
      }
    });
  };

  return (
    <div className="mt-3">
      <div className="flex flex-wrap items-center gap-2">
        {tags.map((t) => (
          <span
            key={t.id}
            className={cn(
              "inline-flex items-center gap-1 pl-2.5 pr-1.5 py-1 rounded-full text-[12px] font-semibold",
              TAG_STYLES[t.color] ?? TAG_STYLES.slate,
            )}
          >
            {t.name}
            <button
              type="button"
              onClick={() => unassign(t.id)}
              disabled={pending}
              aria-label={`Quitar ${t.name}`}
              className="rounded-full hover:bg-black/10 p-0.5"
            >
              <X size={11} strokeWidth={2.5} />
            </button>
          </span>
        ))}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className={cn(
            "text-[12px] inline-flex items-center gap-1 border border-dashed rounded-full px-2.5 py-1 transition-colors",
            open
              ? "border-primary text-primary"
              : "border-line-2 text-muted hover:text-primary",
          )}
        >
          <Plus size={12} strokeWidth={2.5} />
          Agregar
        </button>
      </div>

      {open && (
        <div className="mt-3 rounded-xl border border-line bg-surface-2 p-3 flex flex-col gap-3">
          {available.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {available.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => assign(t.id)}
                  disabled={pending}
                  className={cn(
                    "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[12px] font-semibold hover:opacity-80",
                    TAG_STYLES[t.color] ?? TAG_STYLES.slate,
                  )}
                >
                  <Plus size={11} strokeWidth={2.5} />
                  {t.name}
                </button>
              ))}
            </div>
          )}

          {/* Crear nueva */}
          <div className="flex flex-col gap-2 border-t border-line pt-3">
            <span className="text-[11px] text-muted font-semibold">
              Crear etiqueta
            </span>
            <div className="flex items-center gap-1.5">
              {COLOR_KEYS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setNewColor(c)}
                  aria-label={`Color ${c}`}
                  className={cn(
                    "w-5 h-5 rounded-full transition-transform",
                    TAG_SWATCHES[c],
                    newColor === c
                      ? "ring-2 ring-offset-1 ring-fg scale-110"
                      : "opacity-70 hover:opacity-100",
                  )}
                />
              ))}
            </div>
            <div className="flex items-center gap-2">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    createAndAssign();
                  }
                }}
                placeholder="Nombre de la etiqueta"
                maxLength={60}
                className="flex-1 min-w-0 rounded-lg bg-surface border border-line px-2.5 py-1.5 text-[13px] focus-visible:border-primary"
              />
              <button
                type="button"
                onClick={createAndAssign}
                disabled={pending || !newName.trim()}
                className="shrink-0 rounded-lg bg-primary text-white text-[12px] font-semibold px-3 py-1.5 hover:bg-primary-hover disabled:opacity-50"
              >
                Crear
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Notas internas ──────────────────────────────────────────────────

function NotesManager({
  id,
  notes,
  onNotesChange,
}: {
  id: number;
  notes: InternalNote[];
  onNotesChange: (n: InternalNote[]) => void;
}) {
  const { toast } = useToast();
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [pending, start] = useTransition();

  const add = () => {
    const body = draft.trim();
    if (!body) return;
    start(async () => {
      const r = await createNoteAction(id, body);
      if (r.ok) {
        onNotesChange([r.data, ...notes]);
        setDraft("");
      } else {
        toast.error("No se pudo crear", { description: r.error });
      }
    });
  };

  const saveEdit = (noteId: number) => {
    const body = editDraft.trim();
    if (!body) return;
    start(async () => {
      const r = await updateNoteAction(id, noteId, body);
      if (r.ok) {
        onNotesChange(notes.map((n) => (n.id === noteId ? r.data : n)));
        setEditingId(null);
      } else {
        toast.error("No se pudo guardar", { description: r.error });
      }
    });
  };

  const remove = (noteId: number) => {
    start(async () => {
      const r = await deleteNoteAction(id, noteId);
      if (r.ok) onNotesChange(notes.filter((n) => n.id !== noteId));
      else toast.error("No se pudo eliminar", { description: r.error });
    });
  };

  return (
    <div className="mt-3 flex flex-col gap-3">
      {/* Composer */}
      <div className="flex flex-col gap-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Agrega una nota interna…"
          rows={2}
          maxLength={2000}
          className="no-focus-outline w-full resize-none rounded-xl bg-amber-soft/40 border border-amber/30 px-3 py-2 text-[12.5px] placeholder:text-muted focus-visible:border-amber"
        />
        {draft.trim() && (
          <button
            type="button"
            onClick={add}
            disabled={pending}
            className="self-end rounded-lg bg-primary text-white text-[12px] font-semibold px-3 py-1.5 hover:bg-primary-hover disabled:opacity-50"
          >
            Guardar nota
          </button>
        )}
      </div>

      {notes.length === 0 ? (
        <p className="text-[12px] text-muted">Sin notas todavía.</p>
      ) : (
        notes.map((n) => (
          <div
            key={n.id}
            className="rounded-xl bg-amber-soft/50 border border-amber/20 px-3 py-2.5 group"
          >
            {editingId === n.id ? (
              <div className="flex flex-col gap-2">
                <textarea
                  autoFocus
                  value={editDraft}
                  onChange={(e) => setEditDraft(e.target.value)}
                  rows={3}
                  maxLength={2000}
                  className="no-focus-outline w-full resize-none rounded-lg bg-surface border border-line px-2.5 py-1.5 text-[12.5px] focus-visible:border-primary"
                />
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    className="text-[12px] text-muted hover:text-fg px-2 py-1"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={() => saveEdit(n.id)}
                    disabled={pending}
                    className="rounded-lg bg-primary text-white text-[12px] font-semibold px-3 py-1 hover:bg-primary-hover disabled:opacity-50"
                  >
                    Guardar
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="text-[12.5px] text-fg whitespace-pre-wrap leading-relaxed">
                  {n.body}
                </p>
                <div className="mt-1.5 flex items-center justify-between gap-2">
                  <span className="text-[10.5px] text-muted font-mono truncate">
                    {n.author_name ?? "—"} · {fmtDateTime(n.created_at)}
                  </span>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(n.id);
                        setEditDraft(n.body);
                      }}
                      aria-label="Editar nota"
                      className="text-muted hover:text-primary p-1"
                    >
                      <Pencil size={13} strokeWidth={2} />
                    </button>
                    <button
                      type="button"
                      onClick={() => remove(n.id)}
                      disabled={pending}
                      aria-label="Eliminar nota"
                      className="text-muted hover:text-danger p-1"
                    >
                      <Trash2 size={13} strokeWidth={2} />
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        ))
      )}
    </div>
  );
}

// ── Primitivos ──────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] uppercase tracking-[0.6px] font-semibold text-muted">
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-[12px] text-muted shrink-0">{label}</span>
      <span className="text-[12.5px] font-medium text-right">{value}</span>
    </div>
  );
}

function HistoryRow({
  dot,
  label,
  meta,
}: {
  dot: string;
  label: string;
  meta: string;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <span className={cn("w-2 h-2 rounded-full shrink-0", dot)} />
      <span className="text-[12.5px] flex-1">{label}</span>
      <span className="text-[11px] text-muted font-mono shrink-0">{meta}</span>
    </div>
  );
}
