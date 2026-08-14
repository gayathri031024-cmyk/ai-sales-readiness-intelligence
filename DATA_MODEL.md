# DATA_MODEL.md

**Project:** AI Sales Readiness Intelligence
**Phase:** 2 — Data Model
**Scope check:** MVP only. No tables for RAG/knowledge documents, coaching, drills, organizations, or manager rollups — those are added in later migrations when their phases (10–21) arrive. Adding them now would be exactly the kind of premature infrastructure the Product Scope Gate exists to prevent.

---

## 1. Entity-Relationship Overview

```
users ──────────┐
                 │ 1
                 ▼ *
          conversations ───────► scenarios ───────► buyer_personas
                 │ 1                  │ 1
                 │ *                  │ *
                 ▼                    ▼
             messages      scenario_competency_thresholds
                 │
                 │
        ┌────────┼────────────────┐
        ▼ 1                       ▼ 1
   buyer_state_history       evaluations ───────► competencies
   (per conversation,             │ 1
    append-only log)              │ *
                                  ▼
                              evidence

conversations 1───1 readiness_results
```

## 2. Tables

### `users`
Minimal — MVP runs effectively single-user, but every conversation is still owned by a user id, so multi-user support later doesn't require a schema migration on this table.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| email | text, unique | |
| created_at | timestamptz | default now() |

### `buyer_personas`
| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| name | text | e.g. "Enterprise CFO" |
| description | text | sophistication, concerns, tone |
| base_state | jsonb | starting values for trust/patience/budget_sensitivity/interest |
| created_at | timestamptz | |

MVP ships one row here (Enterprise CFO), per Phase 0.

### `scenarios`
| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| title | text | e.g. "Enterprise CFO — Price Objection" |
| buyer_persona_id | uuid, FK → buyer_personas.id | |
| product_context | text | what's being sold, MVP: static seed text |
| known_objection | text | e.g. "price" |
| difficulty | text | enum-like: easy/standard/hard |
| max_turns | int | end-condition input |
| created_at | timestamptz | |

MVP ships one row here.

### `scenario_competency_thresholds`
Normalizes the "readiness requires Objection Handling ≥ 70 for this scenario" rule from Phase 0/1 — deliberately its own table rather than a jsonb blob, since the readiness engine reads it directly and it should be trivial to unit-test.

| Column | Type | Notes |
|---|---|---|
| scenario_id | uuid, FK → scenarios.id | |
| competency_id | uuid, FK → competencies.id | |
| min_score | int | required for READY on this competency |

PK: `(scenario_id, competency_id)`

### `competencies`
Lookup table rather than hardcoded strings scattered across evaluation/readiness code.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| key | text, unique | `discovery` / `objection_handling` / `closing` |
| display_name | text | |

MVP ships exactly 3 rows, per Phase 0. (Value Articulation, Negotiation, Product Knowledge, Pain Identification are **not** seeded yet — adding them is a Milestone 3 data change, not a schema change, since the table already supports it.)

### `conversations`
| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| user_id | uuid, FK → users.id | |
| scenario_id | uuid, FK → scenarios.id | |
| status | text | `in_progress` / `completed` |
| current_buyer_state | jsonb | **never included in any API response schema** — see ARCHITECTURE.md §6 |
| end_reason | text, nullable | `turn_limit` / `patience_exhausted` / `explicit_close` |
| started_at | timestamptz | |
| completed_at | timestamptz, nullable | |

Index: `(user_id)`, `(scenario_id)`

### `messages`
| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| conversation_id | uuid, FK → conversations.id | |
| turn_index | int | ordering |
| sender | text | `rep` / `buyer` |
| content | text | |
| classified_intent | text, nullable | populated for rep messages by the conversation graph's classification node |
| created_at | timestamptz | |

Index: `(conversation_id, turn_index)` composite, for ordered transcript retrieval.

### `buyer_state_history`
Append-only log of state after each turn. Not user-facing — this exists specifically to let us test the Phase 0 assumptions (does state leak, is state evolution sane) during Phase 6/15/18, not as a product feature.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| conversation_id | uuid, FK → conversations.id | |
| turn_index | int | |
| state | jsonb | |
| created_at | timestamptz | |

Index: `(conversation_id, turn_index)`

### `evaluations`
One row per competency per conversation (not one row per conversation) — keeps evidence cleanly scoped and matches "every score has evidence" as a per-competency guarantee, not a bundled one.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| conversation_id | uuid, FK → conversations.id | |
| competency_id | uuid, FK → competencies.id | |
| score | int | 0–100 |
| diagnosis | text | |
| impact | text | |
| recommendation | text | |
| created_at | timestamptz | |

Index: `(conversation_id)`, unique on `(conversation_id, competency_id)`

### `evidence`
| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| evaluation_id | uuid, FK → evaluations.id | |
| message_id | uuid, FK → messages.id | ties evidence to an actual transcript line — this is what prevents hallucinated quotes from being untraceable |
| quote | text | extracted excerpt |
| note | text, nullable | why this line matters |

Index: `(evaluation_id)`

### `readiness_results`
| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| conversation_id | uuid, FK → conversations.id, unique | one verdict per conversation |
| verdict | text | `READY` / `NOT_READY` / `AT_RISK` |
| reasoning | text | which competency/competencies failed threshold, human-readable |
| thresholds_snapshot | jsonb | the exact thresholds used at decision time, for auditability if scenario thresholds change later |
| computed_at | timestamptz | |

---

## 3. Explicitly Deferred (no tables created now)

`organizations`, `products` (catalog), `knowledge_documents` (RAG), `coaching_sessions`, `drills`, `reassessments`, `skill_graph_edges`, `manager_rollups`. Each belongs to a later phase (10–21) and will arrive as its own migration when that phase starts — not pre-built now.

## 4. Migration Strategy (for Phase 3)

Alembic, one migration per meaningful schema change (not one giant initial migration per table) — mirrors the "commit after a small working unit" discipline already established for the project. UUID primary keys throughout (`gen_random_uuid()` via `pgcrypto`), to avoid sequential-ID enumeration even though MVP auth is minimal.

---

## PHASE 2 CHECKPOINT

**Objective:** Design the MVP-scoped data model and competency model before any code is written.
**Completed:** All MVP entities defined with columns, relationships, and indexes; readiness thresholds normalized into their own table; evidence tied to actual message rows (not free text) to keep it traceable; deferred entities explicitly listed.
**Files Created/Modified:** `DATA_MODEL.md`, `DECISIONS.md` (updated), `CHANGELOG.md` (updated), `PROJECT_STATE.md` (updated)
**Architecture Changes:** None to `ARCHITECTURE.md` itself — this phase implements the DB layer already described there.
**Tests Performed:** N/A — no code yet.
**Acceptance Criteria:** Every MVP module (scenario, buyer, conversation, evaluation, readiness) has backing tables; competency thresholds are scenario-specific and queryable without a jsonb blob; evidence is traceable to a specific message row; no non-MVP tables introduced.
**Known Problems:** None yet — P3: `buyer_state_history` grows unbounded per conversation; fine at prototype scale, worth a retention/pruning note before real deployment (Phase 20/21).
**Technical Debt:** None yet.
**Manual Verification:** Review the schema against the Phase 1 architecture and Phase 0 competency list (Discovery, Objection Handling, Closing) — confirm nothing extra crept in and nothing needed is missing.
**Expected Result:** Approval, or specific pushback on a table/relationship.
**Regression Test:** N/A.
**Decision:** PASS (recommended) — **pending your review**

---

**STOP.** Waiting for `CHECKPOINT PASSED` before starting Phase 3 — Project Foundation (this is where actual code and the repo scaffold begin).
