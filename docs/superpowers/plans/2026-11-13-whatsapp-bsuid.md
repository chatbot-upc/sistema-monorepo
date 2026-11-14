# WhatsApp BSUID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task.

**Goal:** Receive and answer WhatsApp text from users whose phone number Meta omits, preserving contact identity, conversation history and academic-data isolation.

**Architecture:** Add optional phone/BSUID wire identities and an internal stable student ID. Persist BSUID aliases under a business portfolio scope, keep phone-based academic datasets separate, and resolve outbound recipients from current persisted identities rather than stale task arguments. Retain a nullable legacy conversation phone column during migration.

**Tech Stack:** FastAPI, Pydantic 2, SQLAlchemy 2, PostgreSQL/Alembic, Celery, Next.js/TypeScript.

**Spec:** /Users/renzolenes/Desktop/Proyectos/brain/outputs/chatbot-upc-bsuid-research-20261113/investigacion-y-propuesta.txt

## Global Constraints

- No deployment, real WhatsApp sends, Mantis edits or production-data exports.
- Work only in this isolated checkout; do not change the source repository or its existing dirty documents.
- Send phone in `to` or BSUID in `recipient`, exactly one; `recipient_type` remains `individual`. Preserve BSUID verbatim; never phone-normalize it.
- BSUID is scoped to the business portfolio; WABA entry.id and business phone_number_id are different identifiers.
- Phone and BSUID are optional independently; text requires at least one usable identity. Preserve HMAC verification, wamid deduplication, quoting and delivery-status updates.
- Never use BSUID, username, display name or arbitrary shared contact cards to find an academic profile or billing account.
- Preserve existing student/conversation/message/history/tag IDs and current phone-only behavior. Do not automatically merge contacts on conflicting identities.
- Keep Graph API version unchanged. Retain compatibility with queued phone-based task arguments during coordinated application rollout.
- Unknown BSUID contacts can use general RAG; personal academic information requires a safely observed phone association.

## Review Focus

- Rotation events can contain system.user_id without top-level from/from_user_id; history must follow the prior alias without transferring academic data to an unrelated contact.
- Two concurrent first messages must not create duplicate contacts or open conversations for one identity.
- Multiple contacts in a webhook batch must match by identifiers and never by array position.
- A delayed job must use the current recipient after identity rotation, and never send to another scope/sender.
- A failed status without contacts and a forwarded-only context without id must remain acceptable.

---

### Task 1: Meta wire contract and sender

**Files:** Modify `apps/api/src/chatbot_api/schemas/whatsapp.py`, `services/whatsapp_webhook_service.py`, `services/whatsapp_service.py`, `core/settings.py`; test `apps/api/tests/test_whatsapp_bsuid_contract.py` and existing webhook/sender tests.

**Interfaces:** Produce `ParsedInboundMessage` with optional `from_phone`, `from_user_id`, `from_parent_user_id`, `username`, `identity_scope`, `business_phone_number_id`; retain existing text/timestamp/display_name/context fields and old task JSON defaults. Produce `ParsedIdentityChange` with message ID, scope/sender, system event type, new/previous user IDs, optional observed old phone, new_wa_id routing metadata and parent IDs; `extract_identity_changes(payload)` returns these. `send_message(*, to: str | None = None, recipient: str | None = None, body: str, context: dict | None = None)` rejects missing or dual recipients before dev bypass. Produce a shared scope helper based on configured `META_BUSINESS_PORTFOLIO_ID`; if unset, namespace by business sender ID (safe isolated fallback, documented). If both unavailable, reject BSUID text explicitly rather than persist an unscoped identifier. Phone-only legacy fixtures remain valid.

- [ ] Write tests for phone-only, BSUID-only, both, parent/username, exact opaque preservation, mixed contact ordering, rotation system events, context without id, failed statuses with no recipient, malformed text missing identity, and exact outbound JSON for both recipient modes.
- [ ] Implement optional Meta fields, event-type validation and extraction with per-message identifier matching; derive metadata phone_number_id and scope. Extract system events separately rather than treat them as user text. No arbitrary vCard linking.
- [ ] Implement sender with exclusive to/recipient fields; preserve context, read markers, wamid parsing and client lifecycle. Add portfolio setting without changing Graph version.
- [ ] Run targeted contract, webhook and sender tests; record commands/results and commit only task changes.

### Task 2: Durable identity, migration and application flow

**Files:** Create migration `apps/api/alembic/versions/0024_whatsapp_identities.py`, identity model/repository/service and tests. Modify `models/student.py`, `models/conversation.py`, `models/__init__.py`, `repositories/student.py`, `repositories/conversation.py`, `workers/conversation.py`, `api/webhooks.py`, `services/conversation_service.py`, `schemas/conversation.py`, `schemas/student.py`, related tests and notification call sites as necessary.

**Interfaces:** Consume Task 1 parsed fields and sender. Add `students.id` BigInteger PK and nullable unique actual `phone_e164`; add `conversations.student_id` FK and nullable legacy `student_phone`. Map aliases in `whatsapp_identities` with scope, user_id (String160), student_id, sender ID, parent ID and username; unique(scope,user_id). Central service resolves inbound contact, current recipient and identity changes. Keep old phone repository/task entry points compatible. API `student_phone`/`phone_e164` become nullable; expose stable `student_id`, nullable `whatsapp_user_id` and `whatsapp_username` in conversation list/detail and StudentRead if needed. Profile/billing lookup uses actual safely linked phone only. Define precise additional service signatures in task report for frontend handoff.

- [ ] Add migration tests with preexisting phone rows/conversation/message/tag/profile/billing data and upgrade assertions preserving IDs and links. Refuse downgrade when BSUID-only data cannot be represented losslessly; test reversible phone-only downgrade if supported.
- [ ] Implement backfill before constraints, stable student identity and alias lookup; transactional locking/upsert protects concurrent contact/conversation creation. Prefer matching scoped BSUID, safely bind observed phone only when no conflict; ambiguous identities must not merge histories or expose academic data. Keep old aliases for history but mark the current destination after a rotation; duplicate rotations are idempotent. Handle phone-change events by clearing stale academic phone associations when identity no longer owns that phone. system.wa_id is routing metadata (new_wa_id), never confirmed academic phone; wait for a later actual from observation to associate a new phone.
- [ ] Integrate webhook scheduling for identity events and process them durably; update all automatic, welcome, billing, escalation, delayed and manual sends to resolve current recipient from the conversation contact. Keep inbound message deduplication, takeover behavior and events. Do not silently send across configured business senders.
- [ ] Update list/detail/profile/history repository joins to stable student_id and nullable phone handling, preserve old entry points used by existing tests and queued jobs.
- [ ] Test phone-to-BSUID continuity, BSUID-only processing/general reply and manual sends, hiding/reappearing phone, both rotation types, duplicate events, identity conflicts, separate scopes, same-identity concurrency, delayed recipient refresh, no academic lookup on unknown BSUID, full migration upgrade and old queued jobs.
- [ ] Run relevant tests then full existing API suite against disposable testcontainers (no real external messages), record results and commit.

### Task 3: Panel compatibility and operational guidance

**Files:** Modify `apps/web/src/lib/api/conversations.ts`, `apps/web/src/app/(app)/conversations/_components/ConversationsClient.tsx`, `ContactPanel.tsx`, `apps/web/src/app/(app)/dashboard/page.tsx` and any direct consumers found by rg. Create `docs/WhatsApp_BSUID.md`; modify env examples if present. Add frontend unit coverage only if test infrastructure already exists; otherwise verify TypeScript and focused rendering.

**Interfaces:** Consume Task 2 nullable phone and stable student_id / whatsapp_user_id / whatsapp_username fields, as documented in its report. Show available name, phone or user ID clearly; usernames are display metadata only. No phone-only string operations on null values.

- [ ] Update all conversation/StudentRead types and phone-dependent displays/search/initials; no fabricated phone numbers, no crash when phone is absent. Keep current UI styling/layout.
- [ ] Document official Meta field contract and links, `META_BUSINESS_PORTFOLIO_ID` setup, safe sender-scoped fallback and requirement to configure portfolio before rollout, coordinated API/worker migration and draining old queues, downgrade guard, collision/unknown-profile handling, QA simulator matrix and live delivery limitation.
- [ ] Run TypeScript checking and existing lint/build checks as practical; record any unrelated baseline failures. Document tests for all four official Meta simulator cases, rotations and status receipts without sending live messages.
- [ ] Commit task changes; give exact commands/results and any remaining limitations for whole-branch review.
