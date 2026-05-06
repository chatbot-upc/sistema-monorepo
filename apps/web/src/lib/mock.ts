// Mock data shared by all pages

export type ConversationStatus = "active" | "escalated" | "closed" | "pending";

export interface Conversation {
  id: string;
  name: string;
  phone: string;
  preview: string;
  time: string;
  status: ConversationStatus;
  unread?: number;
  gradient: "amber" | "coral" | "violet" | "mint" | "blue" | "rose";
  initials: string;
  studentId?: string;
  career?: string;
  cycle?: string;
  email?: string;
}

export const conversations: Conversation[] = [
  {
    id: "mp-001",
    name: "María Paula Rivera",
    phone: "+51 999 888 777",
    preview: "y si ya me matriculé pero no pagué?",
    time: "09:16",
    status: "escalated",
    unread: 2,
    gradient: "amber",
    initials: "MP",
    studentId: "U20211234",
    career: "Ingeniería de Sistemas",
    cycle: "6° (2026-1)",
    email: "u20211234@upc.edu.pe",
  },
  {
    id: "jc-002",
    name: "Juan Carlos Méndez",
    phone: "+51 988 777 666",
    preview: "no entiendo el cargo por reincorporación",
    time: "09:12",
    status: "escalated",
    unread: 5,
    gradient: "coral",
    initials: "JC",
    studentId: "U20203456",
    career: "Administración",
    cycle: "8° (2026-1)",
    email: "u20203456@upc.edu.pe",
  },
  {
    id: "rp-003",
    name: "Roberto Paz",
    phone: "+51 977 666 555",
    preview: "mi pago no se refleja en el sistema",
    time: "08:41",
    status: "escalated",
    unread: 1,
    gradient: "violet",
    initials: "RP",
    studentId: "U20226789",
    career: "Ingeniería Industrial",
    cycle: "4° (2026-1)",
    email: "u20226789@upc.edu.pe",
  },
  {
    id: "ls-004",
    name: "Lucía Soto",
    phone: "+51 977 666 555",
    preview: "gracias por la ayuda!",
    time: "09:08",
    status: "closed",
    gradient: "mint",
    initials: "LS",
    studentId: "U20214567",
  },
  {
    id: "dr-005",
    name: "Diego Ramírez",
    phone: "+51 966 555 444",
    preview: "qué requisitos necesito para matrícula",
    time: "08:54",
    status: "active",
    gradient: "blue",
    initials: "DR",
    studentId: "U20227891",
  },
  {
    id: "vg-006",
    name: "Valentina García",
    phone: "+51 955 444 333",
    preview: "cuáles son las fechas de matrícula?",
    time: "08:32",
    status: "active",
    gradient: "rose",
    initials: "VG",
    studentId: "U20218234",
  },
  {
    id: "sc-007",
    name: "Sebastián Castro",
    phone: "+51 944 333 222",
    preview: "listo, ya hice el pago",
    time: "08:14",
    status: "closed",
    gradient: "mint",
    initials: "SC",
    studentId: "U20226543",
  },
  {
    id: "am-008",
    name: "Andrea Mendoza",
    phone: "+51 933 222 111",
    preview: "a qué hora abre la oficina?",
    time: "07:58",
    status: "closed",
    gradient: "violet",
    initials: "AM",
    studentId: "U20212345",
  },
];

export interface BubbleMessage {
  id: string;
  author: "student" | "bot" | "admin";
  text: string;
  time: string;
  intent?: { name: string; score: number };
  source?: string;
  adminName?: string;
}

export const sampleThread: BubbleMessage[] = [
  {
    id: "1",
    author: "student",
    text: "hola buenas tardes",
    time: "09:14",
    intent: { name: "saludo", score: 0.98 },
  },
  {
    id: "2",
    author: "bot",
    text: "¡Hola! Soy el asistente de matrícula UPC 👋 Puedo ayudarte con fechas, costos, requisitos o cursos.",
    time: "09:14",
  },
  {
    id: "3",
    author: "student",
    text: "cuando es el pago del primer ciclo",
    time: "09:15",
    intent: { name: "fechas_pago", score: 0.72 },
  },
  {
    id: "4",
    author: "bot",
    text: "El pago del primer ciclo vence el **15 de mayo**. Después de esa fecha aplica un recargo del 5% por mora.",
    time: "09:15",
    source: "RAG: costos_2026.pdf",
  },
  {
    id: "5",
    author: "student",
    text: "y si ya me matriculé pero no pagué?",
    time: "09:16",
    intent: { name: "fallback", score: 0.41 },
  },
  {
    id: "6",
    author: "admin",
    text: "Hola María Paula, te ayudo con eso. El plazo de pago se extiende 7 días con un recargo del 5%. Si ya pasaron, contáctanos por mesa de ayuda.",
    time: "09:19",
    adminName: "Renzo",
  },
  {
    id: "7",
    author: "student",
    text: "muchas gracias 🙏",
    time: "09:20",
    intent: { name: "despedida", score: 0.91 },
  },
];

export interface Document {
  id: string;
  name: string;
  type: "PDF" | "MD" | "TXT";
  size: string;
  status: "indexed" | "indexing" | "draft" | "error";
  indexedAt: string | null;
  chunks: number;
}

export const documents: Document[] = [
  {
    id: "d1",
    name: "matricula_2026.pdf",
    type: "PDF",
    size: "1.2 MB",
    status: "indexed",
    indexedAt: "2026-04-25",
    chunks: 142,
  },
  {
    id: "d2",
    name: "costos_2026.pdf",
    type: "PDF",
    size: "840 KB",
    status: "indexed",
    indexedAt: "2026-04-23",
    chunks: 86,
  },
  {
    id: "d3",
    name: "requisitos_carreras.md",
    type: "MD",
    size: "12 KB",
    status: "indexed",
    indexedAt: "2026-04-20",
    chunks: 24,
  },
  {
    id: "d4",
    name: "cronograma_2026_1.pdf",
    type: "PDF",
    size: "640 KB",
    status: "indexing",
    indexedAt: null,
    chunks: 0,
  },
  {
    id: "d5",
    name: "faqs_pagos.md",
    type: "MD",
    size: "8 KB",
    status: "draft",
    indexedAt: null,
    chunks: 0,
  },
];

export interface Intent {
  id: string;
  name: string;
  examples: number;
  threshold: number;
  active: boolean;
  samples: string[];
}

export const intents: Intent[] = [
  {
    id: "i1",
    name: "fechas_pago",
    examples: 42,
    threshold: 0.65,
    active: true,
    samples: [
      "cuando es el pago del primer ciclo",
      "fecha límite de pago",
      "hasta cuando puedo pagar",
      "cuándo vence el pago",
    ],
  },
  {
    id: "i2",
    name: "costos_matricula",
    examples: 38,
    threshold: 0.7,
    active: true,
    samples: [
      "cuánto cuesta la matrícula",
      "precio de la pensión",
      "cuánto pago por ciclo",
    ],
  },
  {
    id: "i3",
    name: "requisitos",
    examples: 51,
    threshold: 0.6,
    active: true,
    samples: [
      "qué documentos necesito",
      "requisitos para matricularme",
      "qué tengo que llevar",
    ],
  },
  {
    id: "i4",
    name: "cursos",
    examples: 28,
    threshold: 0.65,
    active: true,
    samples: ["qué cursos hay disponibles", "lista de materias"],
  },
  {
    id: "i5",
    name: "cronograma",
    examples: 22,
    threshold: 0.7,
    active: true,
    samples: ["fechas de exámenes", "cuándo empiezan las clases"],
  },
];

export const topIntents = [
  { name: "requisitos", value: 312, color: "coral" as const },
  { name: "costos_matricula", value: 268, color: "amber" as const },
  { name: "fechas_pago", value: 214, color: "primary" as const },
  { name: "cursos", value: 158, color: "violet" as const },
  { name: "cronograma", value: 128, color: "blue" as const },
];

// =============================================================
// Mutable in-memory store
// =============================================================

export interface ConvMeta {
  tags: string[];
  notes: string;
  favorite: boolean;
  blocked: boolean;
}

const EMPTY_META: ConvMeta = {
  tags: [],
  notes: "",
  favorite: false,
  blocked: false,
};

const EMPTY_THREAD: BubbleMessage[] = [];

let _conversations: Conversation[] = [...conversations];
let _documents: Document[] = [...documents];
let _intents: Intent[] = [...intents];
const _threads: Record<string, BubbleMessage[]> = {
  "mp-001": [...sampleThread],
};
const _meta: Record<string, ConvMeta> = {};

const subscribers = new Set<() => void>();
const notify = () => subscribers.forEach((fn) => fn());

export function subscribe(fn: () => void): () => void {
  subscribers.add(fn);
  return () => {
    subscribers.delete(fn);
  };
}

// ---- Reads ----
export const getConversations = (): Conversation[] => _conversations;
export const getDocuments = (): Document[] => _documents;
export const getIntents = (): Intent[] => _intents;
export const getThread = (convId: string): BubbleMessage[] =>
  _threads[convId] ?? EMPTY_THREAD;
export const getMeta = (convId: string): ConvMeta =>
  _meta[convId] ?? EMPTY_META;

// ---- Conversation mutations ----
export function closeConversation(id: string) {
  _conversations = _conversations.map((c) =>
    c.id === id ? { ...c, status: "closed" as const, unread: undefined } : c
  );
  notify();
}

export function addConversation(conv: Conversation) {
  _conversations = [conv, ..._conversations];
  notify();
}

export function appendMessage(convId: string, msg: BubbleMessage) {
  const current = _threads[convId] ?? [];
  _threads[convId] = [...current, msg];
  notify();
}

export function addTag(convId: string, tag: string) {
  const m = getMeta(convId);
  if (m.tags.includes(tag)) return;
  _meta[convId] = { ...m, tags: [...m.tags, tag] };
  notify();
}

export function removeTag(convId: string, tag: string) {
  const m = getMeta(convId);
  _meta[convId] = { ...m, tags: m.tags.filter((t) => t !== tag) };
  notify();
}

export function saveNotes(convId: string, notes: string) {
  _meta[convId] = { ...getMeta(convId), notes };
  notify();
}

export function toggleFavorite(convId: string) {
  const m = getMeta(convId);
  _meta[convId] = { ...m, favorite: !m.favorite };
  notify();
}

export function blockConversation(convId: string) {
  _meta[convId] = { ...getMeta(convId), blocked: true };
  _conversations = _conversations.map((c) =>
    c.id === convId ? { ...c, status: "closed" as const } : c
  );
  notify();
}

// ---- Document mutations ----
export function addDocument(doc: Omit<Document, "id">): string {
  const id = `d-${Date.now()}`;
  _documents = [{ ...doc, id }, ..._documents];
  notify();
  return id;
}

export function deleteDocument(id: string) {
  _documents = _documents.filter((d) => d.id !== id);
  notify();
}

export function reindexDocument(id: string) {
  _documents = _documents.map((d) =>
    d.id === id ? { ...d, status: "indexing" as const } : d
  );
  notify();
  setTimeout(() => {
    _documents = _documents.map((d) =>
      d.id === id
        ? {
            ...d,
            status: "indexed" as const,
            indexedAt: new Date().toISOString().slice(0, 10),
            chunks: Math.floor(Math.random() * 180) + 20,
          }
        : d
    );
    notify();
  }, 1500);
}

// ---- Intent mutations ----
export function addIntent(intent: Omit<Intent, "id">): string {
  const id = `i-${Date.now()}`;
  _intents = [{ ...intent, id }, ..._intents];
  notify();
  return id;
}

export function updateIntent(id: string, patch: Partial<Intent>) {
  _intents = _intents.map((i) => (i.id === id ? { ...i, ...patch } : i));
  notify();
}

export function deleteIntent(id: string) {
  _intents = _intents.filter((i) => i.id !== id);
  notify();
}
