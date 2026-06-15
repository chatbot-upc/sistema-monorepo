#!/usr/bin/env python3
"""
UML Class Diagram — chatbot-upc.

Layer order (top→bottom):
  1. API Endpoints
  2. Services / Workers
  3. Repositories          ← between Services and Models avoids layer-skipping arrows
  4. Domain Models
  5. Infrastructure

Each edge only crosses ONE layer → no arrow tunnels through boxes.
"""

# ── Layout ────────────────────────────────────────────────────────────────────
W   = 210   # class width
GAP = 18    # horizontal gap
LH  = 16    # text line height
SPC = 55    # vertical gap between layers

# 7 columns
C = [20 + i * (W + GAP) for i in range(7)]
# C[0]=20  C[1]=248  C[2]=476  C[3]=704  C[4]=932  C[5]=1160  C[6]=1388

# Layer top-y (package bg top)
L_API   = 40
L_SVC   = 270
L_REPO  = 540
L_MOD   = 800
L_INFRA = 1040

# Colour palette
PAL = {
    "api":    ("#dae8fc", "#6c8ebf"),   # blue
    "svc":    ("#d5e8d4", "#82b366"),   # green
    "worker": ("#fff2cc", "#d6b656"),   # yellow
    "repo":   ("#e1d5e7", "#9673a6"),   # purple
    "model":  ("#ffe6cc", "#d79b00"),   # orange
    "infra":  ("#f8cecc", "#b85450"),   # red/pink
}


# ── Primitives ────────────────────────────────────────────────────────────────
def esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _h(attrs: list[str], methods: list[str], stereotype: str) -> int:
    hdr = 42 if stereotype else 28
    ah  = len(attrs)   * LH + 10 if attrs   else 0
    mh  = len(methods) * LH + 10 if methods else 0
    sep = 8 if attrs and methods else 0
    return hdr + ah + sep + mh


def uml(cid: str, name: str, x: int, y: int,
        stereotype: str, attrs: list[str], methods: list[str],
        fill: str, stroke: str, w: int = W) -> list[str]:

    hdr  = 42 if stereotype else 28
    hval = f"&lt;&lt;{esc(stereotype)}&gt;&gt;&#xa;{esc(name)}" if stereotype else esc(name)
    ah   = len(attrs)   * LH + 10 if attrs   else 0
    mh   = len(methods) * LH + 10 if methods else 0
    sep  = 8 if attrs and methods else 0
    tot  = hdr + ah + sep + mh

    out: list[str] = []
    out.append(
        f'<mxCell id="{cid}" value="{hval}" '
        f'style="swimlane;fontStyle=1;align=center;startSize={hdr};'
        f'fillColor={fill};strokeColor={stroke};fontSize=12;rounded=0;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{tot}" as="geometry" />'
        f'</mxCell>'
    )
    yc = hdr
    if attrs:
        t = "&#xa;".join(esc(a) for a in attrs)
        out.append(
            f'<mxCell id="{cid}_a" value="{t}" '
            f'style="text;align=left;verticalAlign=top;spacingLeft=5;'
            f'overflow=hidden;fontSize=11;fillColor=none;strokeColor=none;" '
            f'vertex="1" parent="{cid}">'
            f'<mxGeometry y="{yc}" width="{w}" height="{ah}" as="geometry" /></mxCell>'
        )
        yc += ah
    if attrs and methods:
        out.append(
            f'<mxCell id="{cid}_s" value="" style="line;strokeColor={stroke};fillColor=none;" '
            f'vertex="1" parent="{cid}">'
            f'<mxGeometry y="{yc}" width="{w}" height="{sep}" as="geometry" /></mxCell>'
        )
        yc += sep
    if methods:
        t = "&#xa;".join(esc(m) for m in methods)
        out.append(
            f'<mxCell id="{cid}_m" value="{t}" '
            f'style="text;align=left;verticalAlign=top;spacingLeft=5;'
            f'overflow=hidden;fontSize=11;fillColor=none;strokeColor=none;" '
            f'vertex="1" parent="{cid}">'
            f'<mxGeometry y="{yc}" width="{w}" height="{mh}" as="geometry" /></mxCell>'
        )
    return out


def pkg(pid: str, label: str, x: int, y: int, pw: int, ph: int) -> str:
    return (
        f'<mxCell id="{pid}" value="{esc(label)}" '
        f'style="text;fontStyle=1;fontSize=12;fillColor=#f5f5f5;strokeColor=#666;'
        f'dashed=1;align=left;verticalAlign=top;spacingLeft=8;spacingTop=5;" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{pw}" height="{ph}" as="geometry" />'
        f'</mxCell>'
    )


def rel(rid: str, src: str, tgt: str, label: str = "", kind: str = "dep") -> str:
    S = {
        "inh": "endArrow=block;endFill=0;startArrow=none;endSize=12;",
        "rea": "dashed=1;endArrow=block;endFill=0;startArrow=none;endSize=12;",
        "cmp": "endArrow=diamondThin;endFill=1;startArrow=none;",
        "ass": "endArrow=open;endFill=0;startArrow=none;",
        "dep": "dashed=1;endArrow=open;endFill=0;startArrow=none;",
    }
    st = (
        f"edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;rounded=1;"
        f"{S.get(kind, S['dep'])}fontSize=10;labelBackgroundColor=#ffffff;"
    )
    return (
        f'<mxCell id="{rid}" value="{esc(label)}" style="{st}" '
        f'edge="1" source="{src}" target="{tgt}" parent="1">'
        f'<mxGeometry relative="1" as="geometry" /></mxCell>'
    )


# ── Diagram ───────────────────────────────────────────────────────────────────
def build() -> str:
    parts: list[str] = []

    # helper: flatten list-of-lists
    def add(*items):
        for it in items:
            if isinstance(it, list):
                parts.extend(it)
            else:
                parts.append(it)

    # ── Package backgrounds ────────────────────────────────────────────────────
    PW = C[6] + W + 10   # full canvas width
    add(
        pkg("P1", "<<layer 1>>  Presentation — API Endpoints",  10, L_API,   PW, 200),
        pkg("P2", "<<layer 2>>  Application — Workers & Services", 10, L_SVC, PW, 240),
        pkg("P3", "<<layer 3>>  Repository — Data Access",      10, L_REPO,  PW, 230),
        pkg("P4", "<<layer 4>>  Domain — ORM Models",           10, L_MOD,   PW, 215),
        pkg("P5", "<<layer 5>>  Infrastructure — Core",         10, L_INFRA, PW, 230),
    )

    # ── Layer 1 — API ─────────────────────────────────────────────────────────
    CY = L_API + 28
    a = PAL["api"]

    add(uml("R_wh",  "WebhookRouter",      C[0], CY, "router",
            ['prefix="/api/webhooks"'], ["+ verify_token() : int",
                                         "+ receive_event() : 202"], *a))
    add(uml("R_au",  "AuthRouter",         C[1], CY, "router",
            ['prefix="/api/v1/auth"'],    ["+ login() : TokenResponse",
                                           "+ refresh() : TokenResponse",
                                           "+ me() : AdminRead"], *a))
    add(uml("R_cv",  "ConversationsRouter",C[2], CY, "router",
            ['prefix="/api/v1/conversations"'],
            ["+ list(...) : Page",
             "+ detail(id) : ConvDetail",
             "+ messages(id) : Page"], *a))
    add(uml("R_dc",  "DocumentsRouter",    C[3], CY, "router",
            ['prefix="/api/v1/documents"'],
            ["+ list(...) : Page",
             "+ upload(file) : DocumentRead",
             "+ delete(id) : 204",
             "+ summary() : DocumentSummary"], *a))
    add(uml("R_in",  "IntentsRouter",      C[4], CY, "router",
            ['prefix="/api/v1/intents"'], ["+ list(active) : Page",
                                           "+ detail(id) : IntentRead"], *a))
    add(uml("R_mo",  "MonitoringRouter",   C[5], CY, "router",
            ['prefix="/api/v1/monitoring"'], ["+ health(db) : MonitoringHealth"], *a))
    add(uml("R_rp",  "ReportsRouter",      C[6], CY, "router",
            ['prefix="/api/v1/reports"'], ["+ dashboard() : dict",
                                           "+ conversations() : list",
                                           "+ intents() : list"], *a))

    # ── Layer 2 — Services ────────────────────────────────────────────────────
    CY = L_SVC + 28
    w, g = PAL["worker"], PAL["svc"]

    add(uml("S_pm", "ProcessMessageWorker", C[0], CY, "celery",
            ["max_retries = 3"],
            ["+ process_incoming_message(",
             "    parsed, correlation_id)",
             "Flujo: upsert_student →",
             "  get_or_create_conversation →",
             "  classify_intent →",
             "  rag_service.answer() →",
             "  whatsapp_service.send()"], *w))
    add(uml("S_iw", "IngestDocumentWorker", C[1], CY, "celery",
            ["max_retries = 2"],
            ["+ ingest_document(document_id)",
             "Flujo: load_file(s3_key) →",
             "  chunk_text() →",
             "  embed_chunks() →",
             "  bulk_insert_chunks() →",
             "  update status=indexed"], *w))
    add(uml("S_ic", "IntentClassifierService", C[2], CY, "service",
            ["- _index : _IntentIndex | None",
             "- _threshold : float = 0.55",
             "- _llm : ChatOpenAI | None"],
            ["+ classify(db, text) : dict",
             "- _sbert_classify(text) : tuple",
             "- _llm_classify(text) : tuple",
             "+ reset_index()"], *g))
    add(uml("S_rg", "RAGService",            C[3], CY, "service",
            ["- _agent : AgentExecutor | None"],
            ["+ answer(user_text, corr_id) : dict",
             "- _get_agent() : AgentExecutor",
             "  tools: search_knowledge_base,",
             "         escalate_to_human"], *g))
    add(uml("S_wa", "WhatsAppService",        C[4], CY, "service",
            ["- _client : AsyncClient | None"],
            ["+ send_message(to, body) : str",
             "- _get_client() : AsyncClient"], *g))
    add(uml("S_cs", "ConversationService",    C[5], CY, "service", [],
            ["+ list_paginated(db, ...) : Page",
             "+ get_detail(db, id) : ConvDetail",
             "+ list_messages(db, id) : Page"], *g))
    add(uml("S_ds", "DocumentService",        C[6], CY, "service", [],
            ["+ upload_document(db, ...) : Doc",
             "+ delete_document(db, id)"], *g))

    # ── Layer 3 — Repositories ────────────────────────────────────────────────
    CY = L_REPO + 28
    r = PAL["repo"]

    add(uml("RP_base", "BaseRepository[M, C, U]", C[0], CY, "abstract",
            ["- model : type[M]"],
            ["+ get(db, id) : M | None",
             "+ list(db, skip, limit) : list[M]",
             "+ count(db) : int",
             "+ create(db, schema) : M",
             "+ update(db, obj, schema) : M",
             "+ delete(db, id) : bool"], *r))
    add(uml("RP_st",  "StudentRepository",        C[1], CY, "", [],
            ["+ upsert_by_phone(db, phone, name)",
             "+ get_by_phone(db, phone) : Student"], *r))
    add(uml("RP_cv",  "ConversationRepository",   C[2], CY, "", [],
            ["+ list_filtered(db, ...) : list",
             "+ get_with_messages(db, id)",
             "+ get_or_create_open(db, phone)"], *r))
    add(uml("RP_ms",  "MessageRepository",        C[3], CY, "", [],
            ["+ list_by_conversation(db, id)",
             "+ create_inbound(db, ...) : Message",
             "+ create_bot(db, ...) : Message"], *r))
    add(uml("RP_it",  "IntentRepository",         C[4], CY, "", [],
            ["+ list_filtered(db, active) : list",
             "+ get_by_name(db, name) : Intent"], *r))
    add(uml("RP_dc",  "DocumentRepository",       C[5], CY, "", [],
            ["+ list_filtered(db, ...) : list",
             "+ get_by_sha256(db, hash)",
             "+ status_summary(db) : dict"], *r))
    add(uml("RP_ck",  "DocumentChunkRepository",  C[6], CY, "", [],
            ["+ bulk_insert_chunks(db, chunks)"], *r))

    # ── Layer 4 — Domain Models ───────────────────────────────────────────────
    CY = L_MOD + 28
    m = PAL["model"]

    add(uml("M_stu", "Student",       C[0], CY, "",
            ["# phone_e164 : str  [PK]",
             "  display_name : str | None",
             "  first_seen_at : datetime",
             "  last_seen_at : datetime"], [], *m))
    add(uml("M_adm", "Admin",         C[1], CY, "",
            ["# id : int  [PK]",
             "  cognito_sub : str",
             "  email : str  [UNIQUE]",
             "  name : str",
             "  role : AdminRole",
             "  active : bool"], [], *m))
    add(uml("M_cnv", "Conversation",  C[2], CY, "",
            ["# id : int  [PK]",
             "  student_phone : str  [FK]",
             "  status : ConversationStatus",
             "  opened_at : datetime",
             "  closed_at : datetime | None",
             "  meta : dict"], [], *m))
    add(uml("M_msg", "Message",       C[3], CY, "",
            ["# id : int  [PK]",
             "  conversation_id : int  [FK]",
             "  role : MessageRole",
             "  content : str",
             "  intent_id : int | None  [FK]",
             "  latency_ms : int | None"], [], *m))
    add(uml("M_int", "Intent",        C[4], CY, "",
            ["# id : int  [PK]",
             "  name : str  [UNIQUE]",
             "  examples : list[str]",
             "  active : bool"], [], *m))
    add(uml("M_doc", "Document",      C[5], CY, "",
            ["# id : int  [PK]",
             "  title : str",
             "  sha256 : str  [UNIQUE]",
             "  s3_key : str",
             "  status : DocumentStatus"], [], *m))
    add(uml("M_ck",  "DocumentChunk", C[6], CY, "",
            ["# id : int  [PK]",
             "  document_id : int  [FK]",
             "  chunk_text : str",
             "  embedding : Vector(1536)",
             "  chunk_index : int"], [], *m))

    # ── Layer 5 — Infrastructure ──────────────────────────────────────────────
    CY = L_INFRA + 28
    i = PAL["infra"]

    add(uml("I_cfg", "Settings",              C[0], CY, "BaseSettings",
            ["DATABASE_URL : str",
             "OPENAI_API_KEY : str",
             "META_ACCESS_TOKEN : str",
             "COGNITO_USER_POOL_ID : str",
             "CELERY_BROKER_URL : str",
             "intent_sbert_threshold : float"],
            ["+ get_settings() : Settings  [lru_cache]"], *i))
    add(uml("I_whs", "WhatsAppWebhookService",C[1], CY, "service", [],
            ["+ verify_signature(body, sig) : bool",
             "+ extract_messages(payload) : list"], *i))
    add(uml("I_stg", "Storage",               C[2], CY, "ABC", [],
            ["+ save(key, data) : str",
             "+ get(key) : bytes",
             "+ delete(key) : bool"], *i))
    add(uml("I_lfs", "LocalFileStorage",      C[3], CY, "",
            ["- base_dir : Path"],
            ["+ save(key, data) : str",
             "+ get(key) : bytes",
             "+ delete(key) : bool"], *i))
    add(uml("I_cel", "CeleryApp",             C[4], CY, "Celery",
            ["broker : redis://...",
             "backend : redis://...",
             "include : [workers.*]"], [], *i))
    add(uml("I_db",  "AsyncSession",          C[5], CY, "SQLAlchemy", [],
            ["+ execute(stmt) : Result",
             "+ commit()",
             "+ rollback()"], *i))
    add(uml("I_psh", "PushService",           C[6], CY, "service",
            ["- _app : firebase.App | None"],
            ["+ register_device(db, admin_id, ...)",
             "+ notify_admin(db, admin_id, ...) : int"], *i))

    # ── Relationships ─────────────────────────────────────────────────────────

    # [A] Repo inheritance (same layer, horizontal)
    for rid, src in [
        ("ri_st", "RP_st"),
        ("ri_cv", "RP_cv"),
        ("ri_ms", "RP_ms"),
        ("ri_it", "RP_it"),
        ("ri_dc", "RP_dc"),
        ("ri_ck", "RP_ck"),
    ]:
        add(rel(rid, src, "RP_base", "", "inh"))

    # [B] LocalStorage implements Storage (same layer)
    add(rel("r_lfs_stg", "I_lfs", "I_stg", "", "rea"))

    # [C] API → Services (adjacent layer, mostly same column)
    add(rel("r_wh_pm",  "R_wh", "S_pm",  "dispatches", "dep"))
    add(rel("r_dc_ds",  "R_dc", "S_ds",  "uses",        "dep"))
    add(rel("r_cv_cs",  "R_cv", "S_cs",  "uses",        "dep"))

    # [D] Services → Services (same layer)
    add(rel("r_pm_ic",  "S_pm", "S_ic",  "classify()",  "dep"))
    add(rel("r_pm_rg",  "S_pm", "S_rg",  "answer()",    "dep"))
    add(rel("r_pm_wa",  "S_pm", "S_wa",  "send()",      "dep"))
    add(rel("r_ds_iw",  "S_ds", "S_iw",  "dispatch",    "dep"))

    # [E] Services → Repositories (adjacent layer)
    add(rel("r_pm_rpcv", "S_pm", "RP_cv", "uses", "dep"))
    add(rel("r_pm_rpms", "S_pm", "RP_ms", "uses", "dep"))
    add(rel("r_pm_rpst", "S_pm", "RP_st", "uses", "dep"))
    add(rel("r_iw_rpdc", "S_iw", "RP_dc", "uses", "dep"))
    add(rel("r_iw_rpck", "S_iw", "RP_ck", "uses", "dep"))
    add(rel("r_ic_rpit", "S_ic", "RP_it", "uses", "dep"))
    add(rel("r_cs_rpcv", "S_cs", "RP_cv", "uses", "dep"))
    add(rel("r_ds_rpdc", "S_ds", "RP_dc", "uses", "dep"))

    # [F] Repositories → Models (adjacent layer, same column → straight arrows)
    add(rel("r_rpst_mstu", "RP_st", "M_stu", "manages", "ass"))
    add(rel("r_rpcv_mcnv", "RP_cv", "M_cnv", "manages", "ass"))
    add(rel("r_rpms_mmsg", "RP_ms", "M_msg", "manages", "ass"))
    add(rel("r_rpit_mint", "RP_it", "M_int", "manages", "ass"))
    add(rel("r_rpdc_mdoc", "RP_dc", "M_doc", "manages", "ass"))
    add(rel("r_rpck_mck",  "RP_ck", "M_ck",  "manages", "ass"))

    # [G] Model associations (same layer, FK relationships)
    add(rel("r_mcnv_mstu", "M_cnv", "M_stu", "student_phone [FK]", "ass"))
    add(rel("r_mmsg_mcnv", "M_msg", "M_cnv", "conversation_id [FK]", "ass"))
    add(rel("r_mmsg_mint", "M_msg", "M_int", "intent_id [FK] 0..1", "ass"))
    add(rel("r_mck_mdoc",  "M_ck",  "M_doc", "document_id [FK]",    "cmp"))

    # ── XML ───────────────────────────────────────────────────────────────────
    body = "\n  ".join(
        p if isinstance(p, str) else "\n  ".join(p)
        for p in parts
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        'pageWidth="1640" pageHeight="1320" math="0" shadow="0">\n'
        '  <root>\n'
        '    <mxCell id="0" />\n'
        '    <mxCell id="1" parent="0" />\n  '
        + body +
        '\n  </root>\n</mxGraphModel>\n'
    )


if __name__ == "__main__":
    xml = build()
    out = "/Users/renzolenes/Desktop/Proyectos/chatbot-upc/docs/class_diagram.drawio"
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Written → {out}  ({len(xml):,} bytes)")
