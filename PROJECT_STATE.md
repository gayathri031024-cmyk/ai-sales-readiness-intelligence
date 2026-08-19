# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 11 — Targeted Drills
**Current Checkpoint:** Phase 11 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED); Phase 6 — Adaptive AI Buyer (PASSED); Phase 7 — Conversation Engine (PASSED); Phase 8 — Evaluation Engine (PASSED); Phase 9 — Readiness Engine (PASSED); Phase 10 — AI Coach (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 10`)

**Current Objective:** Get sign-off that Targeted Drills correctly turns Phase 10's coaching output into a focused practice assignment — deterministically, with zero LLM calls and therefore zero new hallucination surface, correctly scoped to competency-focus only (not a fabricated new scenario, not a guessed-at reassessment mechanism).

**Completed Work:**
- Phases 0–10 approved (see CHANGELOG.md for detail)
- Phase 11 Targeted Drills built and verified by automated test + live manual smoke test:
  - Verified the Phase 10 baseline first (167/167 tests, clean git state at `83ab555`). Unlike Phase 9/10, no unexplained pre-existing files were found at the start of this phase.
  - Read MASTER_PROMPT.md's TRAINING LOOP and `DATA_MODEL.md`'s explicit deferral of `drills` and `reassessments` as two separate tables before writing any code.
  - `app/drills/generation.py` — pure, deterministic `generate_drill()`: zero LLM calls (structurally — no provider parameter exists in its signature, test-enforced), reassembling Phase 9's priority pick, Phase 8's evaluation diagnosis/recommendation, and Phase 10's already-verified coaching points (filtered to the priority competency) into a title, focus reason, and instructions. No new claim is ever introduced.
  - `app/drills/service.py` — orchestrates as one transaction; idempotent (behavioral consistency, not cost avoidance — this module is already free); never triggers Phase 10's coaching computation itself, even lazily.
  - New `drills` table via Alembic migration `7b1f3c9d2a6e` (chains from head `c054f45455ae`) — verified against a fresh DB, schema matches the ORM model column-by-column.
  - `POST`/`GET /conversations/{id}/drill`, wired into `main.py`. 409 if coaching hasn't run yet; 404 for unknown conversations / not-yet-generated drills.
  - 16 new backend tests (183 total, all passing) — deterministic generation at the unit level, full API-level pipeline, zero-LLM guarantee, idempotency, hidden-state protection, public API schema shape.
  - Explicitly scoped **out**: a distinct practice scenario (MVP has only one scenario — `practice_scenario_id` always equals the origin conversation's own, honestly documented rather than faked); reassessment (the training loop's fourth step — `DATA_MODEL.md` defers it to its own separate table with zero specification, and guessing at it would violate this phase's explicit rule against fabricating requirements).
  - Live manual verification against a real running `uvicorn` server: create → close → drill-before-coaching → 409 → evaluate → readiness → coaching → drill → correct competency and assembled instructions with no `LLM_API_KEY` set → GET returns identical data → 404 for unknown conversation.
  - Checked for and confirmed no accidental artifacts are tracked via `git status --ignored`.
  - Frontend not touched — a drill card would sit downstream of a coaching card that doesn't exist in the frontend yet. `npm run build` re-verified clean as a regression check only.

**In Progress:** Awaiting your review of Phase 11.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin Phase 12 — Adaptive Difficulty (scaling scenario/buyer difficulty based on demonstrated competency — explicitly out of Phase 11's own boundary, which produced a fixed-difficulty targeted drill only, no difficulty scaling, no reassessment loop, no scenario library).

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- Drills have no frontend at all yet — API-only, same reasoning and same owner decision as the coaching frontend gap.
- The training loop's reassessment step is not implemented — a rep can practice again today via the existing conversation flow, but the system doesn't yet automatically link that practice back to a specific drill. Owner: a dedicated future phase, not Phase 12.
- "Targeted" drills currently target only competency focus, not a distinct practice scenario — MVP has one scenario. Owner: whichever future phase adds a scenario library.
- Coaching has no frontend at all yet — API-only (unchanged from Phase 10).
- Phase 9 frontend Result integration not visually screenshot-verified in an actual browser (unchanged).
- Phase 5 and Phase 7 frontend integration still carry the same pre-existing, unresolved visual-verification gap (unchanged).
- No scripted buyer opening line (unchanged, Phase 7 decision, still under your review).

**Known P3:**
- Drill does not auto-regenerate if coaching/readiness/evaluation ever changes after the fact — deliberate, behavioral-consistency posture.
- Coaching's priority pick carries no cross-competency causal reasoning — correctly scoped out per MASTER_PROMPT.md, owner Phase 14.
- Coaching session does not auto-regenerate if readiness/evaluation ever changes — deliberate.
- `AT_RISK_MARGIN = 10` is a placeholder judgment call, not calibrated against real transcripts — owner Phase 15.
- Readiness verdict does not auto-recompute if evaluation scores ever change — deliberate.
- Rejected (hallucinated/ungrounded) evidence candidates are silently dropped, not logged anywhere — owner Phase 15/18.
- `buyer_state_history` unbounded growth — owner Phase 20/21.
- Dev-mode auto schema creation needs an explicit production guard — owner Phase 21.
- MVP scenario seeding rides the same dev-only guard — owner Phase 21.
- `AnthropicProvider` still never exercised against the real Anthropic API for any module — owner final integration.
- Turn-submission responses include full message history on every turn — irrelevant at MVP scale.
- MVP is single-user via a synthetic default user — intentional, `user_id` FK already in place for Milestone 3.

**Technical Debt:** Same as before, plus the P3 items above.
**Last Successful Test:** `pytest -v` (backend) — 183 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors, unaffected (no frontend files changed this phase). `alembic upgrade head` — clean against a fresh DB, all three migrations apply in order, all 13 tables present. Live `uvicorn` smoke test confirmed correct request/response behavior end to end.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 11.
