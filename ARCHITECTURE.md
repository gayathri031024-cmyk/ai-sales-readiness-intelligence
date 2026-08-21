# ARCHITECTURE.md

**Project:** AI Sales Readiness Intelligence
**Phase:** 1 — System Architecture
**Scope:** MVP only (Milestone 1, per Phase 0). RAG, manager dashboard, voice, multi-tenant security, and full skill graph are explicitly out of scope here — see "Explicitly Deferred" at the bottom.

---

## 1. High-Level Architecture

```
                 React + TypeScript (Vite, Tailwind)
                              │
                              ▼
                     FastAPI (single service)
                              │
        ┌─────────────┬───────────────┬───────────────┐
        ▼             ▼               ▼               ▼
   Scenario Mod   Conversation     Evaluation      Readiness
                     Module          Module          Module
        │             │               │               │
        └─────────────┴───────┬───────┴───────────────┘
                              ▼
                    AI Orchestration Layer
                    (LangGraph + structured
                     output LLM calls)
                              │
                              ▼
                        PostgreSQL
                (scenarios, conversations,
                 messages, evaluations,
                 readiness_results)
```

One backend service. **Modular monolith** — clear module boundaries in code, single deployable unit, single database. No microservices; no justification exists yet for that complexity.

## 2. Frontend Architecture

React + TypeScript + Vite + Tailwind. Three screens only — this is intentionally small:

1. **Start Scenario** — pick/confirm the (single, MVP) scenario, see persona summary, start.
2. **Conversation** — chat UI, rep types messages, buyer replies stream back. "End conversation" action.
3. **Result** — evidence-based evaluation per competency, then the readiness verdict with reasoning.

State management: no global state library needed at this size. Local component state (`useState`) for UI, and the backend conversation record as the single source of truth — fetched, not duplicated client-side. This keeps the frontend disposable and avoids sync bugs between client and server state (important since buyer hidden state must never live in the browser at all — see Security).

## 3. Backend Architecture — Module Boundaries

```
backend/
  api/            → FastAPI routers (thin, no business logic)
  scenario/       → scenario definition + seeding (MVP: one hardcoded scenario)
  buyer/          → AI buyer: hidden state schema + LangGraph graph
  conversation/   → turn persistence, turn-taking, end-condition logic
  evaluation/     → evidence extraction + competency scoring pipeline
  readiness/      → deterministic rules engine (pure Python, no LLM)
  ai/             → shared LLM client, structured-output schemas, retry logic
  db/             → SQLAlchemy models, session, migrations
  core/           → config, logging, error handling
```

Rule: **`readiness/` never calls an LLM.** It only ever reads competency scores + scenario-specific thresholds and returns READY / NOT READY / AT RISK with a reason string built from which threshold(s) failed. This is the module boundary that makes the "LLM proposes, deterministic logic decides" principle enforceable in code, not just in a prompt.

## 4. AI Architecture

Two distinct AI components — deliberately not the same graph, because they have different shapes:

**A. Conversation Graph (LangGraph)** — stateful, multi-turn, needs looping:

```
receive_rep_message
        ↓
classify_rep_behavior (structured output: intent, tactic used)
        ↓
update_buyer_state (trust / patience / budget_sensitivity / interest —
                     deterministic deltas based on classified behavior,
                     not a free-form LLM number)
        ↓
generate_buyer_reply (LLM, constrained system prompt: current state
                       + persona + explicit "never reveal numeric
                       state or reasoning" instruction)
        ↓
check_end_conditions (turn limit / explicit close attempt /
                       patience below threshold) ──► loop back to
                                                      receive_rep_message
                                                      or end
```

Buyer state updates are **deterministic given the classified behavior**, not a raw LLM guess — the LLM classifies what the rep did; a small Python rule table converts that into state deltas. This is testable and reduces the "buyer leaks/invents state" risk flagged as an assumption in Phase 0.

**B. Evaluation Pipeline** — linear, post-conversation, no looping needed, so a plain sequential pipeline (not LangGraph) is simpler and easier to test:

```
extract_evidence (structured output: list of
                   {turn_index, quote, competency_tag})
        ↓
score_competencies (LLM, constrained to cite only
                     extracted evidence — Discovery,
                     Objection Handling, Closing)
        ↓
readiness_decision (deterministic — see readiness/ module)
```

Every LLM call in both components uses a Pydantic schema for structured output, validated on return; one retry with the validation error fed back to the model; a hard failure after that surfaces as a clear error state, not a hang or a crash.

## 5. Data Flow (single scenario run)

```
Frontend            Backend                          DB / LLM
   │                    │                                │
   │ POST /scenarios/start ─────────────────────────────►│
   │                    │  create conversation record     │
   │                    │  init buyer hidden state ───────► DB
   │◄─── conversation_id, buyer opening line ─────────────│
   │                    │                                │
   │ POST /conversations/{id}/messages ──────────────────►│
   │                    │  run Conversation Graph turn     │
   │                    │  (LLM calls) ───────────────────► LLM
   │                    │  persist turn + updated state ──► DB
   │◄─── buyer reply (state fields excluded) ──────────────│
   │        ... repeat until end condition ...             │
   │                    │                                │
   │ POST /conversations/{id}/complete ───────────────────►│
   │                    │  run Evaluation Pipeline ────────► LLM
   │                    │  run readiness_decision (no LLM)  │
   │                    │  persist evaluation + readiness ─► DB
   │◄─── GET /conversations/{id}/result ────────────────────│
```

## 6. State Management

- **Buyer hidden state**: persisted server-side only, in the conversation record. The API response schema for any message/turn endpoint explicitly excludes state fields at the serializer level — not a "remember not to send it" convention, an enforced schema boundary.
- **Conversation transcript**: persisted turn-by-turn; frontend always re-fetches rather than trusting local history, so a refresh never desyncs from the server record.
- **Frontend state**: UI-only (input box, loading/error flags).

## 7. Error Handling & Reliability

- Structured output validation on every LLM call (Pydantic). One retry with the validation error appended to the prompt; second failure → graceful degraded response, not a crash.
- LLM API failures (timeout, rate limit): retry with backoff, max 2 attempts, then surface an explicit "temporarily unavailable" state to the frontend.
- API-level errors never leak internal prompts, buyer state, or stack traces to the client.

## 8. Security Boundaries (MVP scope)

In scope now:
- All input validated at the API boundary (Pydantic request models).
- DB access via ORM (parameterized queries) — no raw SQL string interpolation.
- Rep messages are never interpolated directly into a system prompt without delimiting, to reduce the risk of the rep instructing the buyer to reveal hidden state (this directly tests the Phase 0 "state leakage" assumption).
- Secrets via environment variables only; `.env` never committed, `.env.example` provided.
- Buyer hidden state excluded from every response schema (see §6).

Explicitly **out of scope for MVP** (deferred to Phase 19 / Milestone 3, per Phase 0 Scope Gate): multi-user auth, org/tenant isolation, rate limiting, full RAG-injection testing (no RAG yet), production-grade secret management. MVP may run as a single-user prototype with a minimal auth stub.

## 9. Deployment Architecture (placeholder)

Not the focus of this phase (deployment is Phase 21 / Milestone 3), but a lightweight target to build against: frontend on a static host (Vercel/Netlify free tier), FastAPI backend on a free/low-cost host (Render/Railway free tier), Postgres on a free-tier hosted instance (Neon/Supabase). Revisit and harden in Phase 21.

## 10. Explicitly Deferred (per Phase 0 Scope Gate)

Not designed in this phase, and intentionally absent from the diagrams above: product/company RAG + pgvector, full 7-competency skill graph with dependency modeling, manager dashboard, root-cause/coaching/drill/reassessment loop, adaptive difficulty, multi-tenant security, voice, multi-agent orchestration beyond the one LangGraph app, microservices. Each has a home later in the phase roadmap; none of them should quietly creep into Milestone 1's implementation.

---

## PHASE 1 CHECKPOINT

**Objective:** Define system architecture for the MVP loop before any code is written.
**Completed:** Frontend/backend/module architecture, AI architecture (conversation graph + evaluation pipeline), data flow, state management, error handling, and security boundaries defined; deployment target sketched at a placeholder level.
**Files Created/Modified:** `ARCHITECTURE.md`, `DECISIONS.md`, `CHANGELOG.md`, `PROJECT_STATE.md` (updated)
**Architecture Changes:** N/A (first architecture pass)
**Tests Performed:** N/A — no code yet
**Acceptance Criteria:** Every module in the MVP scope (scenario, buyer, conversation, evaluation, readiness) has a defined boundary and interface; the deterministic-readiness principle is enforced at the module level, not just described; buyer state exclusion from API responses is architecturally guaranteed, not just a convention.
**Known Problems:** None yet — P2: conversation end-condition logic (turn limit vs. patience threshold vs. explicit close) needs concrete thresholds, deferred to Phase 5/6 design.
**Technical Debt:** None yet.
**Manual Verification:** Review the module boundaries and the two-AI-component split (LangGraph for conversation, plain pipeline for evaluation) — confirm this matches your expectations before any scaffolding is built.
**Expected Result:** Approval, or specific pushback on a module boundary or security decision.
**Regression Test:** N/A.
**Decision:** PASS (recommended) — **pending your review**

---

**STOP.** Waiting for `CHECKPOINT PASSED` before starting Phase 2 — Data Model.
