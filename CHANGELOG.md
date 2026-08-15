# CHANGELOG.md

## Phase 0 — Product Strategy
- Defined target user, buyer/salesperson personas, JTBD, problem statement, core user journey
- Applied Product Scope Gate: classified all roadmap features into MUST HAVE / SHOULD HAVE / LATER / DO NOT BUILD
- Defined MVP boundary: single persona (Enterprise CFO), 3 competencies (Discovery, Objection Handling, Closing), no RAG/coaching/drills/manager view/voice
- Identified assumptions to validate: state leakage, evidence hallucination, scoring consistency
- **Checkpoint: PASSED**

## Phase 1 — System Architecture
- Defined modular monolith architecture (frontend, backend module boundaries, DB)
- Split AI architecture into two components: LangGraph conversation graph + plain sequential evaluation pipeline
- Made readiness engine deterministic (no LLM call) — enforced at module boundary
- Made buyer state updates deterministic given LLM-classified rep behavior
- Made buyer hidden-state exclusion from API responses an architectural (serializer-level) guarantee
- Defined data flow, error handling/retry strategy, MVP-scoped security boundaries, placeholder deployment target
- Explicitly deferred: RAG, full skill graph, manager dashboard, coaching/drills, voice, multi-tenant security
- **Checkpoint: PASSED**

## Phase 2 — Data Model
- Designed MVP-scoped schema: users, buyer_personas, scenarios, scenario_competency_thresholds, competencies, conversations, messages, buyer_state_history, evaluations, evidence, readiness_results
- Normalized readiness thresholds into their own table instead of jsonb, so the deterministic readiness engine can query them directly
- Tied evidence to actual `messages` rows via foreign key, so evidence can never reference a quote that wasn't actually said
- Added `buyer_state_history` as an append-only debug log to test the Phase 0 state-leakage/consistency assumptions
- Explicitly deferred: organizations, products catalog, knowledge_documents, coaching_sessions, drills, reassessments, skill_graph_edges, manager_rollups
- **Checkpoint: PASSED**

## Phase 3 — Project Foundation
- Scaffolded backend: FastAPI app, module skeleton (`scenario/`, `buyer/`, `conversation/`, `evaluation/`, `readiness/`, `ai/`) with future-phase docstrings, config via pydantic-settings, logging setup
- Implemented all 11 SQLAlchemy models from `DATA_MODEL.md`; Alembic autogenerate detected every table correctly on first run; migration verified against a live SQLite DB
- Added `/health` endpoint that actively checks DB connectivity, not just app liveness
- Verified the backend for real: booted `uvicorn` and hit it with `curl` (not just the test client)
- Scaffolded frontend: Vite + React + TypeScript + Tailwind v4; placeholder health-check page only — real screens deliberately deferred to Phase 4
- Verified end-to-end: frontend dev server's `/api` proxy successfully reached the live backend process
- Added CI (GitHub Actions) to run backend tests on push
- Moved all project-memory docs into the repo root, added `PROJECT_PLAN.md`, `KNOWN_ISSUES.md`, `TEST_STATUS.md`, `AI_EVALUATION.md`
- **Checkpoint: PASSED**

## Phase 4 — Core UX
- Built all 3 MVP screens: Start Scenario (briefing), Conversation (live roleplay), Result (evidence-based debrief)
- Established a "briefing room / instrument panel" visual direction (dark theme, amber accent, Space Grotesk + Inter + JetBrains Mono) — deliberately avoided the generic AI-tool default looks
- Built the Evidence Chip as the product's signature UI element, reused consistently across every competency card
- Wired screens together with mock data (`src/mock/`, explicitly marked, typed against `types.ts` so Phases 5–9 swap in real data without a UI rewrite)
- Found and fixed a turn-indexing off-by-one between the mock conversation and mock evidence citations before it could ship as a subtle inconsistency
- Verified visually: built the production bundle, served it, and used Playwright to screenshot and inspect all 3 screens plus the interactive flow between them
- **Checkpoint: PASSED**

## Phase 5 — Scenario Engine
- Seeded the single MVP scenario (Enterprise CFO — Price Objection) into the DB: 1 buyer persona, 1 scenario, 3 competencies (Discovery, Objection Handling, Closing), and their scenario-specific thresholds (60 / 70 / 65) — values and rationale recorded in `DECISIONS.md`, not just a bare migration
- Seed is idempotent (`seed_mvp_scenario`), safe to run on every dev startup; verified with a dedicated unit test and by exercising two full app lifespans against the same SQLite file
- Added `GET /scenarios` and `GET /scenarios/{id}` — thin router in `api/routes/scenario.py`, business logic in `scenario/service.py`, response shape defined by Pydantic schemas in `scenario/schemas.py` (separate from the ORM models, so a DB column change can't silently change the API contract)
- 5 new backend tests: list/detail happy paths, 404 for unknown id, a regression guard that `buyer_persona.base_state` never leaks into any scenario response, and seed idempotency
- Frontend: `StartScenario` now fetches the real scenario via `src/api/scenario.ts` (adapts backend snake_case to the frontend's camelCase `Scenario` type) instead of `src/mock/scenario.ts`, which has been deleted. `Conversation` and `Result` still run on mock data — Phases 6–9 replace those next
- Added a loading state and an explicit error state to `App.tsx` for the scenario fetch, rather than letting a failed fetch render a blank/broken screen
- **Checkpoint: PASSED** (2026-08-15 — you explicitly confirmed `CHECKPOINT PASSED — Phase 5`; automated evidence re-verified at that point: `pytest` 7/7, `npm run build` 0 type errors. The P2 visual-verification item above remains recorded in `KNOWN_ISSUES.md` for the record, not re-litigated.)

## Phase 6 — Adaptive AI Buyer
- Built the shared LLM provider abstraction (`app/ai/provider.py`): an `LLMProvider` protocol, a production `AnthropicProvider` (lazily constructs the SDK client, never requires a key until an actual call is made, raises `LLMUnavailableError` uniformly on any failure), and a fully deterministic `MockLLMProvider` for tests — zero network calls, zero API cost, queued or default-function responses, call recording for assertions
- Built the structured-output helper (`app/ai/structured.py`): JSON parse + Pydantic schema validation, retry-once with the validation error fed back into the prompt, `StructuredOutputError` on a second failure — shared code path Phase 8's evaluation extraction will reuse rather than duplicate
- Built the buyer hidden-state schema (`app/buyer/state.py`): exactly the 4 documented dimensions (trust, patience, budget_sensitivity, interest) from `PHASE_0_PRODUCT_STRATEGY.md` §7 and `DATA_MODEL.md`, bounded [0,100] with clamping on construction, pure `apply_deltas()`
- Built the rep-behavior classification schema and prompts (`app/buyer/classification.py`, `app/buyer/classify.py`): 10-label fixed enum (including `prompt_injection_attempt`), delimited rep-message injection into the user prompt (never in an instruction position), degrades to `UNCLEAR` on any LLM failure rather than raising
- Built the deterministic state-transition rule table (`app/buyer/rules.py`): one fixed `StateDelta` per `RepBehavior` label, pure, no LLM dependency, every label covered (test-enforced)
- Built buyer persona prompting and reply generation (`app/buyer/persona.py`, `app/buyer/response.py`): numeric state is translated to qualitative hints before it ever reaches a prompt (the model literally never sees the numbers), explicit anti-injection system-prompt rules, plus an independent defense-in-depth regex scrubber that catches a reply that talks about hidden mechanics and swaps in a safe in-character fallback line
- Built the LangGraph turn pipeline (`app/buyer/graph.py`): 3 nodes (`classify_rep_behavior` → `update_buyer_state` → `generate_buyer_reply`), single straight line, no branching — every node degrades internally so the graph itself needs no failure branch; compiled once and cached
- Built the public entrypoint (`app/buyer/service.py::run_buyer_turn`) — the seam Phase 7's conversation API will call; deliberately does not touch the database or FastAPI, per the Phase 6 prompt's PHASE BOUNDARY section
- 60 new backend tests across 7 files (67 total, all passing, 0 required LLM API key, verified with all LLM-related env vars unset): state bounds/clamping, rule-table completeness and determinism, provider mock behavior + retry-once + graceful failure, classification schema validation and degradation, reply generation and the leak scrubber (including a deliberate false-positive guard for ordinary "trust"/business language), prompt-injection defense end-to-end through `run_buyer_turn`, LangGraph wiring/state-threading/degradation, and a hidden-state-exposure regression guard on the buyer-turn output specifically
- `LLM_API_KEY` / `LLM_MODEL` env var names were already established in Phase 3's `.env.example` and `core/config.py` — no changes needed there; no real key added or requested
- Phase 5's frontend/backend regression suite re-verified clean after this phase: `pytest` 7/7 (unchanged, now folded into the 67), `npm run build` 0 type errors
- **Checkpoint: PASSED** (2026-08-15 — you explicitly confirmed `CHECKPOINT PASSED — Phase 6` after review; automated evidence re-verified at that point: `pytest` 67/67, `npm run build` 0 type errors.)

## Phase 7 — Conversation Engine
- Verified the Phase 6 baseline before touching anything: `pytest` 67/67 (fresh `dev.db`, all LLM env vars unset), `npm run build` 0 type errors, git history/tag (`v0.7-adaptive-buyer`) confirmed. Discovered `PROJECT_STATE.md` recorded Phase 6 as still awaiting your explicit sign-off — flagged the discrepancy and received `CHECKPOINT PASSED — Phase 6` before starting this phase's work.
- Discovered the DB schema (`conversations`, `messages`, `buyer_state_history`) and their SQLAlchemy models already existed from Phase 2/3 scaffolding, built ahead of need per `DATA_MODEL.md`. **No new Alembic migration was required for Phase 7** — verified by running `alembic upgrade head` against a completely fresh SQLite DB and confirming all 11 tables (including the three above) are created correctly, and that `seed_mvp_scenario()` still behaves idempotently afterward.
- Built `app/conversation/schemas.py` — the public API contract (`ConversationOut`, `MessageOut`), structurally excluding every hidden-state field (`trust`/`patience`/`budget_sensitivity`/`interest`/`current_buyer_state`) and the internal `classified_intent` detail, same "separate from the ORM" pattern as `scenario/schemas.py`
- Built `app/conversation/service.py` — conversation lifecycle and multi-turn orchestration: `start_conversation` (idempotent default-user lookup, persists initial hidden state from the persona's `base_state`), `get_conversation`, `submit_turn` (loads persisted state → calls the **unchanged** `buyer/service.run_buyer_turn()` → persists both messages, the updated hidden state, and a `BuyerStateHistory` row, all inside one DB transaction with rollback on unexpected failure → evaluates end conditions), and `close_conversation` (idempotent explicit-close)
- End conditions implemented exactly per the project's existing fields, no new scoring system invented: turn-limit uses `scenario.max_turns`; patience-exhausted uses `BuyerState`'s own `[0,100]` clamp floor; explicit-close is a dedicated endpoint. `conversations.status` stays the two values `DATA_MODEL.md` already establishes (`in_progress` / `completed`); the three end reasons (`turn_limit` / `patience_exhausted` / `explicit_close`) carry the distinction, exactly as that column was already designed to do. Full reasoning for each choice in `DECISIONS.md`.
- Added `POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/turns`, `POST /conversations/{id}/close` in `app/api/routes/conversation.py`. The LLM provider is injected via a `get_llm_provider` FastAPI dependency (mirrors the existing `get_db` pattern) so tests override it with `MockLLMProvider` — no test ever requires `LLM_API_KEY`/`ANTHROPIC_API_KEY`.
- 27 new backend tests in `test_conversation.py`: creation, retrieval, turn submission, **multi-turn state persistence** (the critical guarantee this phase exists to build — turn 2 is asserted, against exact expected deltas from `buyer/rules.py` and against raw `buyer_state_history` rows, to build on turn 1's persisted state rather than resetting), history ordering with no duplication, all three terminal conditions plus idempotent re-close and rejection of turns against a terminal conversation, hidden-state protection, and failure/degradation behavior (invalid id → 404 not 500, terminal conversation → 409 not 500, no `LLM_API_KEY` set → graceful fallback reply, not a crash)
- 94 total backend tests passing (67 unchanged from Phase 0–6 + 27 new), verified fresh with all LLM-related env vars unset
- Live manual verification against a real running `uvicorn` server (not just `TestClient`): `curl /health` → ok; `curl -X POST /conversations` → correct initial public shape, no hidden-state fields; `curl -X POST /conversations/{id}/turns` with no `LLM_API_KEY` set → graceful-degradation fallback reply, both messages persisted correctly, `turn_count` incremented; `curl /conversations/does-not-exist` → clean 404
- Frontend: added `Conversation`/`TranscriptMessage` types (`types.ts`) and `src/api/conversation.ts` (same snake_case→camelCase adapter pattern as `src/api/scenario.ts`). Rewrote `screens/Conversation.tsx` to drive the real conversation API instead of canned replies — loading/sending/error states, duplicate-submission prevention while a turn is in flight, and a clear terminal-state banner that disables the input and explains why the scenario ended. Deleted the now-orphaned `src/mock/buyer.ts`.
- **Decision surfaced for your review, not resolved unilaterally**: the rep now always speaks first (no scripted opening buyer line) — Phase 6's buyer engine has no code path to generate a reply without first classifying a rep message, and building one solely for a cosmetic opening line would have been exactly the kind of Phase 6 redesign this phase's boundary rules out. See `DECISIONS.md`.
- `npm run build` — 0 type errors after all frontend changes
- **Checkpoint: Phase 7 — awaiting `CHECKPOINT PASSED`**
