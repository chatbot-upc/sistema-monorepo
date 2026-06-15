#!/usr/bin/env python3
"""Generate draw.io ER diagram — clean entity-level connections, hierarchical layout."""

ROW_H    = 26
HDR_H    = 30
W        = 250   # entity width
KW       = 38    # key-label column

# Palette
CLR_STU   = ("#fff2cc", "#d6b656")  # yellow  — student flow
CLR_ADM   = ("#dae8fc", "#6c8ebf")  # blue    — admin
CLR_MSG   = ("#d5e8d4", "#82b366")  # green   — messaging
CLR_DOC   = ("#f8cecc", "#b85450")  # red     — documents
CLR_META  = ("#e1d5e7", "#9673a6")  # purple  — metadata/standalone


def table(eid, name, x, y, fields, fill, stroke):
    """fields: list of (key_label, field_name, field_type)"""
    h = HDR_H + len(fields) * ROW_H
    cells = []
    cells.append(
        f'<mxCell id="{eid}" value="{name}" '
        f'style="shape=table;startSize={HDR_H};container=1;collapsible=0;'
        f'childLayout=tableLayout;fixedRows=1;rowLines=0;fontStyle=1;align=center;'
        f'resizeLast=1;fontSize=13;fillColor={fill};strokeColor={stroke};" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{W}" height="{h}" as="geometry" /></mxCell>'
    )
    for i, (key, fname, ftype) in enumerate(fields):
        yo = HDR_H + i * ROW_H
        rid = f"{eid}_r{i+1}"
        bold = "fontStyle=1;" if key else ""
        cells.append(
            f'<mxCell id="{rid}" value="" '
            f'style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;'
            f'swimlaneBody=0;fillColor=none;collapsible=0;dropTarget=0;'
            f'points=[[0,0.5],[1,0.5]];portConstraint=eastwest;" '
            f'vertex="1" parent="{eid}">'
            f'<mxGeometry y="{yo}" width="{W}" height="{ROW_H}" as="geometry" /></mxCell>'
        )
        cells.append(
            f'<mxCell id="{rid}_k" value="{key}" '
            f'style="shape=partialRectangle;connectable=0;fillColor=none;'
            f'top=0;left=0;bottom=0;right=0;{bold}overflow=hidden;fontSize=10;" '
            f'vertex="1" parent="{rid}">'
            f'<mxGeometry width="{KW}" height="{ROW_H}" as="geometry">'
            f'<mxRectangle width="{KW}" height="{ROW_H}" as="alternateBounds" /></mxGeometry></mxCell>'
        )
        vw = W - KW
        field_label = f"{fname} : {ftype}"
        cells.append(
            f'<mxCell id="{rid}_v" value="{field_label}" '
            f'style="shape=partialRectangle;connectable=0;fillColor=none;'
            f'top=0;left=0;bottom=0;right=0;overflow=hidden;fontSize=11;" '
            f'vertex="1" parent="{rid}">'
            f'<mxGeometry x="{KW}" width="{vw}" height="{ROW_H}" as="geometry">'
            f'<mxRectangle width="{vw}" height="{ROW_H}" as="alternateBounds" /></mxGeometry></mxCell>'
        )
    return "\n  ".join(cells)


def edge(eid, src, tgt, label="", start="ERone", end="ERmany"):
    """Entity-level connection — draw.io auto-routes to nearest border points."""
    style = (
        "edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;"
        f"startArrow={start};startFill=0;"
        f"endArrow={end};endFill=0;"
        "rounded=1;fontSize=10;labelBackgroundColor=#ffffff;"
    )
    return (
        f'<mxCell id="{eid}" value="{label}" style="{style}" '
        f'edge="1" source="{src}" target="{tgt}" parent="1">'
        f'<mxGeometry relative="1" as="geometry" /></mxCell>'
    )


# ─── Layout ──────────────────────────────────────────────────────────────────
# 4 columns, entities arranged top-to-bottom per column.
# Columns:
#   C1 x=20   — student / conversation flow
#   C2 x=300  — intents + association tables
#   C3 x=580  — admin hub + derived tables
#   C4 x=860  — documents + chunks

C1, C2, C3, C4 = 20, 300, 580, 860
GAP = 50


def build():
    parts = []

    # ── Column 1: Student flow ────────────────────────────────────────────────
    y = 20
    parts.append(table("E_students", "students", C1, y, [
        ("PK", "phone_e164",    "VARCHAR"),
        ("",   "display_name",  "VARCHAR"),
        ("",   "first_seen_at", "TIMESTAMPTZ"),
        ("",   "last_seen_at",  "TIMESTAMPTZ"),
    ], *CLR_STU))

    y += HDR_H + 4 * ROW_H + GAP    # 134 + 50 = 184 → y=204
    parts.append(table("E_conversations", "conversations", C1, y, [
        ("PK", "id",             "BIGINT"),
        ("FK", "student_phone",  "VARCHAR"),
        ("",   "status",         "ENUM"),
        ("",   "opened_at",      "TIMESTAMPTZ"),
        ("",   "closed_at",      "TIMESTAMPTZ"),
        ("FK", "closed_by",      "BIGINT"),
        ("FK", "takeover_admin", "BIGINT"),
        ("",   "meta",           "JSONB"),
        ("",   "created_at",     "TIMESTAMPTZ"),
        ("",   "updated_at",     "TIMESTAMPTZ"),
    ], *CLR_STU))

    y += HDR_H + 10 * ROW_H + GAP   # 290 + 50 = 340 → y=544
    parts.append(table("E_messages", "messages", C1, y, [
        ("PK", "id",              "BIGINT"),
        ("FK", "conversation_id", "BIGINT"),
        ("FK", "intent_id",       "BIGINT"),
        ("",   "role",            "ENUM"),
        ("",   "content",         "TEXT"),
        ("",   "retrieved_chunks","JSONB"),
        ("",   "input_tokens",    "INT"),
        ("",   "output_tokens",   "INT"),
        ("",   "model_used",      "VARCHAR"),
        ("",   "latency_ms",      "INT"),
        ("",   "meta_message_id", "VARCHAR"),
        ("",   "created_at",      "TIMESTAMPTZ"),
    ], *CLR_MSG))

    y += HDR_H + 12 * ROW_H + GAP   # 342 + 50 = 392 → y=936
    parts.append(table("E_metrics", "metrics_daily", C1, y, [
        ("PK", "date",                   "DATE"),
        ("",   "conversations_total",    "INT"),
        ("",   "conversations_takeover", "INT"),
        ("",   "messages_total",         "INT"),
        ("",   "avg_response_ms",        "INT"),
        ("",   "total_input_tokens",     "BIGINT"),
        ("",   "total_output_tokens",    "BIGINT"),
        ("",   "intent_distribution",    "JSONB"),
        ("",   "cost_usd",               "NUMERIC"),
    ], *CLR_META))

    # ── Column 2: Intents + associations ─────────────────────────────────────
    y = 204   # aligned with conversations
    parts.append(table("E_intents", "intents", C2, y, [
        ("PK", "id",          "BIGINT"),
        ("",   "name",        "VARCHAR"),
        ("",   "description", "TEXT"),
        ("",   "examples",    "JSONB"),
        ("",   "active",      "BOOLEAN"),
        ("FK", "created_by",  "BIGINT"),
        ("",   "created_at",  "TIMESTAMPTZ"),
        ("",   "updated_at",  "TIMESTAMPTZ"),
    ], *CLR_MSG))

    y += HDR_H + 8 * ROW_H + GAP    # 238 + 50 = 288 → y=492
    parts.append(table("E_conv_intents", "conversation_intents", C2, y, [
        ("PK/FK", "conversation_id", "BIGINT"),
        ("PK/FK", "intent_id",       "BIGINT"),
        ("PK",    "detected_at",     "TIMESTAMPTZ"),
        ("",      "confidence",      "FLOAT"),
    ], "#e1d5e7", "#9673a6"))

    y += HDR_H + 4 * ROW_H + GAP    # 134 + 50 = 184 → y=676
    parts.append(table("E_notifications", "notifications", C2, y, [
        ("PK", "id",              "BIGINT"),
        ("",   "template_name",   "VARCHAR"),
        ("",   "audience_filter", "JSONB"),
        ("",   "scheduled_at",    "TIMESTAMPTZ"),
        ("",   "sent_at",         "TIMESTAMPTZ"),
        ("",   "status",          "ENUM"),
        ("",   "sent_count",      "INT"),
        ("",   "failed_count",    "INT"),
        ("FK", "created_by",      "BIGINT"),
        ("",   "created_at",      "TIMESTAMPTZ"),
        ("",   "updated_at",      "TIMESTAMPTZ"),
    ], *CLR_ADM))

    # ── Column 3: Admin hub ───────────────────────────────────────────────────
    y = 20
    parts.append(table("E_admins", "admins", C3, y, [
        ("PK", "id",          "BIGINT"),
        ("",   "cognito_sub", "VARCHAR"),
        ("",   "email",       "VARCHAR"),
        ("",   "name",        "VARCHAR"),
        ("",   "role",        "ENUM"),
        ("",   "active",      "BOOLEAN"),
        ("",   "created_at",  "TIMESTAMPTZ"),
        ("",   "updated_at",  "TIMESTAMPTZ"),
    ], *CLR_ADM))

    y += HDR_H + 8 * ROW_H + GAP    # 238 + 50 = 288 → y=308
    parts.append(table("E_admin_devices", "admin_devices", C3, y, [
        ("PK", "id",         "BIGINT"),
        ("FK", "admin_id",   "BIGINT"),
        ("",   "fcm_token",  "VARCHAR"),
        ("",   "platform",   "VARCHAR"),
        ("",   "user_agent", "VARCHAR"),
        ("",   "created_at", "TIMESTAMPTZ"),
        ("",   "updated_at", "TIMESTAMPTZ"),
    ], *CLR_ADM))

    y += HDR_H + 7 * ROW_H + GAP    # 212 + 50 = 262 → y=570
    parts.append(table("E_prompt_versions", "prompt_versions", C3, y, [
        ("PK", "id",         "BIGINT"),
        ("",   "name",       "VARCHAR"),
        ("",   "version",    "INT"),
        ("",   "content",    "TEXT"),
        ("",   "active",     "BOOLEAN"),
        ("FK", "created_by", "BIGINT"),
        ("",   "created_at", "TIMESTAMPTZ"),
        ("",   "updated_at", "TIMESTAMPTZ"),
    ], *CLR_ADM))

    # ── Column 4: Documents ───────────────────────────────────────────────────
    y = 20
    parts.append(table("E_documents", "documents", C4, y, [
        ("PK", "id",              "BIGINT"),
        ("",   "title",           "VARCHAR"),
        ("",   "source_type",     "ENUM"),
        ("",   "source_url",      "TEXT"),
        ("",   "s3_key",          "VARCHAR"),
        ("",   "sha256",          "VARCHAR"),
        ("",   "version",         "INT"),
        ("",   "version_history", "JSONB"),
        ("",   "status",          "ENUM"),
        ("",   "error_message",   "TEXT"),
        ("FK", "uploaded_by",     "BIGINT"),
        ("",   "indexed_at",      "TIMESTAMPTZ"),
        ("",   "created_at",      "TIMESTAMPTZ"),
        ("",   "updated_at",      "TIMESTAMPTZ"),
    ], *CLR_DOC))

    y += HDR_H + 14 * ROW_H + GAP   # 394 + 50 = 444 → y=464
    parts.append(table("E_doc_chunks", "document_chunks", C4, y, [
        ("PK", "id",          "BIGINT"),
        ("FK", "document_id", "BIGINT"),
        ("",   "chunk_text",  "TEXT"),
        ("",   "embedding",   "VECTOR(1536)"),
        ("",   "meta",        "JSONB"),
        ("",   "chunk_index", "INT"),
    ], *CLR_DOC))

    # ── Relationships (entity-level, draw.io auto-routes) ─────────────────────
    # students → conversations (1:N)
    parts.append(edge("R_stu_conv",      "E_students",        "E_conversations",   "1:N"))
    # conversations → messages (1:N)
    parts.append(edge("R_conv_msg",      "E_conversations",   "E_messages",        "1:N"))
    # conversations ← → conversation_intents (1:N)
    parts.append(edge("R_conv_ci",       "E_conversations",   "E_conv_intents",    "1:N"))
    # intents ← → conversation_intents (1:N)
    parts.append(edge("R_int_ci",        "E_intents",         "E_conv_intents",    "1:N"))
    # intents → messages (1:N, via intent_id)
    parts.append(edge("R_int_msg",       "E_intents",         "E_messages",        "1:N"))
    # admins → intents (1:N, created_by)
    parts.append(edge("R_adm_int",       "E_admins",          "E_intents",         "1:N"))
    # admins → conversations (0..1:N, closed_by / takeover_admin)
    parts.append(edge("R_adm_conv",      "E_admins",          "E_conversations",   "0..1:N"))
    # admins → admin_devices (1:N)
    parts.append(edge("R_adm_dev",       "E_admins",          "E_admin_devices",   "1:N"))
    # admins → documents (1:N, uploaded_by)
    parts.append(edge("R_adm_doc",       "E_admins",          "E_documents",       "1:N"))
    # admins → notifications (1:N, created_by)
    parts.append(edge("R_adm_notif",     "E_admins",          "E_notifications",   "1:N"))
    # admins → prompt_versions (1:N, created_by)
    parts.append(edge("R_adm_pv",        "E_admins",          "E_prompt_versions", "1:N"))
    # documents → document_chunks (1:N)
    parts.append(edge("R_doc_chunk",     "E_documents",       "E_doc_chunks",      "1:N"))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        'pageWidth="1200" pageHeight="1600" math="0" shadow="0">\n'
        '  <root>\n'
        '    <mxCell id="0" />\n'
        '    <mxCell id="1" parent="0" />\n  '
        + "\n  ".join(parts) +
        '\n  </root>\n</mxGraphModel>\n'
    )
    return xml


if __name__ == "__main__":
    xml = build()
    out = "/Users/renzolenes/Desktop/Proyectos/chatbot-upc/docs/er_diagram.drawio"
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"Written → {out}  ({len(xml):,} bytes)")
