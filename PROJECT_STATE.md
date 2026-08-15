# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 7 — Conversation Engine
**Current Checkpoint:** Phase 7 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 5`; the P2 visual-verification item remains open in KNOWN_ISSUES.md for the record, not re-litigated); Phase 6 — Adaptive AI Buyer (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 6` after review)

**Current Objective:** Get sign-off that the Conversation Engine correctly turns Phase 6's single-turn buyer engine into a persistent, multi-turn sales conversation — turn/state persistence, turn-taking API, end-condition logic, hidden-state protection, and frontend integration — all still fully testable without a real API key, before starting Phase 8 (Evaluation Engine).

**Completed Work:**
- Phases 0–6 approved (see CHANGELOG.md for detail)
- Phase 7 Conversation Engine built and verified by automated test + live manual smoke test:
  - Verified the Phase 6 baseline first (67/67 tests, clean frontend build, git history/tag confirmed) — surfaced and got your explicit sign-off on the Phase 6 checkpoint discrepancy before starting any Phase 7 work
  - Confirmed the DB schema (`conversations`, `messages`, `buyer_state_history`) already existed from Phase 2/3 — **no new Alembic migration needed**; verified via `alembic upgrade head` against a fresh DB
  - `app/conversation/schemas.py` — public API contract (`ConversationOut`, `MessageOut`), structurally excludes every hidden-state field and the internal `classified_intent` detail
  - `app/conversation/service.py` — `start_conversation`, `get_conversation`, `submit_turn` (loads persisted state → calls the unchanged `buyer/service.run_buyer_turn()` → persists messages + updated state + `buyer_state_history` row in one transaction, rollback on unexpected failure → evaluates end conditions), `close_conversation` (idempotent)
  - End conditions use only fields the project already established: `scenario.max_turns` (turn limit), `BuyerState`'s own `[0,100]` clamp floor (patience exhausted), a dedicated close endpoint (explicit close). `status` stays the two values `DATA_MODEL.md` defines (`in_progress`/`completed`); `end_reason` carries the distinction.
  - `app/api/routes/conversation.py` — `POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/turns`, `POST /conversations/{id}/close`; LLM provider injected via a `get_llm_provider` dependency (mirrors `get_db`) so tests never need a real key
  - 27 new backend tests (94 total, all passing) — including a direct, exact-value-asserted proof that turn 2 builds on turn 1's persisted state rather than resetting, the specific guarantee this phase exists to build
  - Live manual smoke test against a real running `uvicorn` server (not just `TestClient`): health check, conversation creation, a full turn submission with graceful degradation (no `LLM_API_KEY` set), and 404 handling — all confirmed correct
  - Frontend: real `Conversation`/`TranscriptMessage` types, `src/api/conversation.ts` adapter, `screens/Conversation.tsx` rewritten to drive the real API (loading/sending/error/terminal states, duplicate-submission guard); deleted the now-orphaned `src/mock/buyer.ts`; `npm run build` clean, 0 type errors
  - One product-UX decision surfaced for your review rather than resolved unilaterally: the rep now always speaks first (no scripted opening buyer line) — see DECISIONS.md, Phase 7

**In Progress:** Awaiting your review of Phase 7.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin Phase 8 — Evaluation Engine (evidence extraction + competency scoring pipeline).

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- Phase 5 frontend integration still not visually verified end-to-end in this sandbox (unchanged, pre-existing).
- Phase 7 frontend conversation UI not visually verified end-to-end in this sandbox — same environment limitation (background dev processes reclaimed between tool calls); backend contract is covered by 27 automated tests plus a live-server manual smoke test, and the frontend type-checks clean against that exact contract.
- No scripted buyer opening line — the rep now always speaks first. A deliberate, documented decision (see DECISIONS.md, Phase 7), not an oversight, but worth your explicit review since it changes the opening UX from the Phase 4 mock.

**Known P3:**
- `buyer_state_history` unbounded growth (Phase 20/21).
- Dev-mode auto schema creation needs an explicit production guard (Phase 21).
- MVP scenario seeding rides the same dev-only guard (Phase 21).
- `AnthropicProvider` still never exercised against the real Anthropic API — Phase 7's live smoke test ran without a key, so it exercised the graceful-degradation path, not the live-model path. Needs one live smoke test once a real `LLM_API_KEY` is added.
- Turn-submission responses include the full message history on every turn (simpler frontend, larger payload as conversations grow) — irrelevant at MVP scale (max 12 turns).
- MVP is single-user via a synthetic default user (`get_or_create_default_user`) — intentional, `user_id` FK already in place for when real auth arrives (Milestone 3).

**Technical Debt:** Same as before, plus the P3 items above.
**Last Successful Test:** `pytest -v` (backend) — 94 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors. `alembic upgrade head` — clean against a fresh DB, all 11 tables present. Live `uvicorn` smoke test — health, conversation creation, turn submission with graceful degradation, and 404 handling all confirmed correct via `curl`.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 7.
