# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 12 — Adaptive Difficulty
**Current Checkpoint:** Phase 12 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED); Phase 6 — Adaptive AI Buyer (PASSED); Phase 7 — Conversation Engine (PASSED); Phase 8 — Evaluation Engine (PASSED); Phase 9 — Readiness Engine (PASSED); Phase 10 — AI Coach (PASSED); Phase 11 — Targeted Drills (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 11`)

**Current Objective:** Get sign-off that Adaptive Difficulty correctly turns Phase 9's readiness verdict and Phase 8's per-competency scores into a deterministic, explainable next-difficulty recommendation (easy/standard/hard) — with zero LLM calls, zero new persistence, and correctly scoped to a recommendation only (not an automatic scenario mutation, not a scenario library, not the still-unbuilt reassessment loop).

**Completed Work:**
- Phases 0–11 approved (see CHANGELOG.md for detail)
- Phase 12 Adaptive Difficulty built and verified by automated test + live manual smoke test:
  - Verified the Phase 11 baseline first: HEAD `8d935a4`, Phase 11 feature commit `b1a08f5` and test commit `fbab6ed` both confirmed present with correct content, working tree clean, 183/183 tests passing fresh (LLM env vars unset), `npm run build` clean, `alembic upgrade head` clean against a fresh DB (13 tables). No unexplained pre-existing Phase 12 work was found at the start of this phase.
  - Read MASTER_PROMPT.md's CORE FEATURES #7 ("Adaptive difficulty based on performance"), this phase's own explicit rules (deterministic, no LLM decides difficulty, no new difficulty levels, no persistence unless genuinely required), and every other control document before writing any code.
  - `app/difficulty/decision.py` — pure, deterministic `recommend_difficulty()`: zero LLM calls (no provider parameter in its signature, test-enforced), reusing `readiness/decision.py::CompetencyResult`/`Verdict` directly rather than inventing new types (same reuse discipline `coaching/priority.py` and `drills/generation.py` established). NOT_READY → step down a difficulty level; AT_RISK → stay; READY → step up only if the narrowest passing competency margin clears a new `READY_COMFORTABLE_MARGIN = 10` constant, otherwise stay. Clamps correctly at either end of the `easy`/`standard`/`hard` ladder.
  - `app/difficulty/service.py` — reads Phase 8's persisted evaluation scores, Phase 5's scenario thresholds, and Phase 9's persisted readiness verdict; requires readiness to already exist (409 if not) and never triggers it itself, same module-boundary discipline as every phase since Phase 9. Deliberately persists nothing — per this phase's own instruction not to create a table absent a genuine persistence requirement, since the recommendation is a pure, free-to-recompute function of already-durable upstream data.
  - One route, `GET /conversations/{id}/difficulty-recommendation` — a single read-only verb rather than the "two verbs" `POST`/`GET` pattern of Phases 9–11, since nothing needs to be triggered or persisted. A deliberate, documented API-shape deviation (see DECISIONS.md, Phase 12), not an oversight.
  - 31 new backend tests (214 total, all passing) — deterministic decision logic at the unit level (all three verdict branches, both ladder-boundary clamps, the exact `READY_COMFORTABLE_MARGIN` boundary on both sides, empty-results and unknown-difficulty error handling, determinism across repeated calls, a parametrized sweep confirming the recommendation is always a valid difficulty level across all 9 verdict×difficulty combinations), full API-level pipeline for all three verdict outcomes, zero-LLM guarantee, precondition/error handling (409 before readiness, 404 for unknown conversations), hidden-state protection, public API schema shape, and identical output across repeated API calls (the "no persistence" analogue of idempotency).
  - Explicitly scoped **out**: any new difficulty level beyond `easy`/`standard`/`hard`; a scenario library or scenario-authoring API for the recommendation to route a rep toward; automatic mutation of any `Scenario` row; the reassessment loop (still a separate, unbuilt future phase per Phase 11's own DECISIONS.md entry, not the same concept as this phase); any LLM call anywhere in the decision path.
  - Live manual verification against a real running `uvicorn` server, no `LLM_API_KEY` set: create → close → difficulty-before-readiness → 409 → evaluate (degraded no-evidence path) → readiness (NOT_READY) → difficulty-recommendation → correct `"decrease"` to `"easy"` → repeated `GET` calls return byte-identical output → 404 for an unknown conversation → route correctly registered in the live OpenAPI schema.
  - Checked for and confirmed no accidental artifacts are tracked via `git status --ignored`; reverted an unrelated `frontend/package-lock.json` metadata-only diff produced incidentally by a regression `npm install` (no dependency version changes — pure lockfile churn, not a Phase 12 change).
  - Frontend not touched — no existing UI slot for a difficulty recommendation and no control document specifying one, same reasoning as Phase 10/11's identical frontend decisions. `npm run build` re-verified clean as a regression check only.

**In Progress:** Awaiting your review of Phase 12.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin the next phase.

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- Adaptive difficulty has no frontend at all yet — API-only, same reasoning and same owner decision as the coaching/drills frontend gaps.
- The recommendation is advisory only against the MVP's single seeded scenario (always `difficulty="standard"`) — there is no second scenario at `"easy"` or `"hard"` for a rep to actually be routed to yet. Owner: whichever future phase adds a scenario library.
- The training loop's reassessment step is still not implemented (unchanged from Phase 11) — this phase does not touch it and is explicitly not "the reassessment mechanism," per this phase's own strict boundaries. Owner: a dedicated future phase.
- Drills have no frontend at all yet — API-only (unchanged from Phase 11).
- Coaching has no frontend at all yet — API-only (unchanged from Phase 10).
- Phase 9 frontend Result integration not visually screenshot-verified in an actual browser (unchanged).
- Phase 5 and Phase 7 frontend integration still carry the same pre-existing, unresolved visual-verification gap (unchanged).
- No scripted buyer opening line (unchanged, Phase 7 decision, still under your review).

**Known P3:**
- `READY_COMFORTABLE_MARGIN = 10` is a placeholder judgment call reusing `AT_RISK_MARGIN`'s value, not independently calibrated against real transcripts — owner Phase 15, same posture as `AT_RISK_MARGIN` itself.
- The difficulty recommendation does not persist, so there is no historical record of what was recommended at a given point in time if upstream evaluation/readiness data ever changes later — deliberate (see DECISIONS.md, Phase 12), revisit only if a future phase needs recommendation history.
- Drill does not auto-regenerate if coaching/readiness/evaluation ever changes after the fact — deliberate, behavioral-consistency posture.
- Coaching's priority pick carries no cross-competency causal reasoning — correctly scoped out per MASTER_PROMPT.md, owner Phase 14.
- Coaching session does not auto-regenerate if readiness/evaluation ever changes — deliberate.
- Readiness verdict does not auto-recompute if evaluation scores ever change — deliberate.
- Rejected (hallucinated/ungrounded) evidence candidates are silently dropped, not logged anywhere — owner Phase 15/18.
- `buyer_state_history` unbounded growth — owner Phase 20/21.
- Dev-mode auto schema creation needs an explicit production guard — owner Phase 21.
- MVP scenario seeding rides the same dev-only guard — owner Phase 21.
- `AnthropicProvider` still never exercised against the real Anthropic API for any module — owner final integration.
- Turn-submission responses include full message history on every turn — irrelevant at MVP scale.
- MVP is single-user via a synthetic default user — intentional, `user_id` FK already in place for Milestone 3.

**Technical Debt:** Same as before, plus the P3 items above.
**Last Successful Test:** `pytest -v` (backend) — 214 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors, unaffected (no frontend files changed this phase). `alembic upgrade head` — clean against a fresh DB, all three migrations apply in order, all 13 tables present (unchanged from Phase 11 — this phase added no migration). Live `uvicorn` smoke test confirmed correct request/response behavior end to end, including the precondition guard and the zero-LLM degraded-mode evaluation path.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 12.
