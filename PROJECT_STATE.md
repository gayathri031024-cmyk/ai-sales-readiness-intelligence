# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 10 — AI Coach
**Current Checkpoint:** Phase 10 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED); Phase 6 — Adaptive AI Buyer (PASSED); Phase 7 — Conversation Engine (PASSED); Phase 8 — Evaluation Engine (PASSED); Phase 9 — Readiness Engine (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 9`)

**Current Objective:** Get sign-off that the AI Coach correctly turns Phase 8's evidence and Phase 9's readiness verdict into evidence-grounded, non-hallucinated coaching — with the priority pick made deterministically (never by the LLM), coaching points that can never cite fabricated evidence, and graceful degradation when the LLM is unavailable.

**Completed Work:**
- Phases 0–9 approved (see CHANGELOG.md for detail)
- Phase 10 AI Coach built and verified by automated test + live manual smoke test:
  - Verified the Phase 9 baseline first: found unexplained, uncommitted `app/coaching/` work already present at the start of this phase (same situation as Phase 9's `readiness/` discovery); `git stash -u`'d it to confirm the actual Phase 9 baseline (144/144 tests) in isolation at commit `b2edc18`, then restored the found work for independent evaluation — not adopted on sight
  - Read the found code against the actual DB schema, `readiness/decision.py`'s existing `CompetencyResult` dataclass (correctly reused, not duplicated), and every relevant control document (MASTER_PROMPT.md's COMPETENCY/SKILL GRAPH and TRAINING LOOP sections, DATA_MODEL.md's explicit "coaching_sessions arrives as its own migration when Phase 10 starts" deferral, PHASE_0_PRODUCT_STRATEGY.md's Milestone 2 scope table) — structurally consistent with all of them — then proven correct by running its own 23-test suite, which passed on the first attempt. Full account in DECISIONS.md, Phase 10.
  - `app/coaching/priority.py` — pure, deterministic `pick_priority()`: worst-gap competency if anything failed its threshold, narrowest-margin competency if everything passed (a READY conversation), ties broken by fixed MVP competency order. The LLM never makes this choice, only writes about the pick it's handed.
  - `app/coaching/generation.py` — the one LLM-touching stage: given only already-persisted Phase 8 evidence/diagnosis and Phase 9's verdict, writes a short coaching summary plus up to 4 points, each optionally citing an evidence id. Never sees the raw transcript or hidden buyer state. Falls back to a fixed deterministic summary (not the LLM) on complete failure.
  - `app/coaching/verification.py` — the Phase 10 analogue of Phase 8's `verify_evidence`: a coaching point's cited evidence id is only kept if it's real, already-Phase-8-verified, and for the exact competency claimed — a fabricated id or a real id from the wrong competency is silently dropped, never persisted.
  - `app/coaching/service.py` — orchestrates the pipeline as one transaction; idempotent (a `coaching_sessions` row, once persisted, is authoritative); never triggers Phase 9's readiness computation itself, even lazily — 409s if readiness isn't done yet.
  - New `coaching_sessions` table via Alembic migration `c054f45455ae` (chains correctly from head `9f7e1a8e08c5`) — verified against a fresh DB, schema matches the ORM model column-by-column. This is the first genuinely new migration since Phase 2/3; `coaching_sessions` was explicitly deferred in `DATA_MODEL.md` specifically until this phase.
  - `POST`/`GET /conversations/{id}/coaching`, wired into `main.py`. 409 if readiness hasn't run yet; 404 for unknown conversations / not-yet-generated coaching.
  - 23 new backend tests (167 total, all passing) — deterministic priority/verification at the unit level, full API-level pipeline, graceful degradation (LLM fully down, priority still exactly correct), idempotency, hidden-state protection, public API schema shape, and a direct proof that a fabricated evidence id never reaches the API response.
  - Live manual verification against a real running `uvicorn` server: create → close → coaching-before-readiness → 409 → evaluate → readiness → coaching → correct deterministic fallback with no `LLM_API_KEY` set (priority correctly identified `objection_handling`) → GET returns identical data → 404 for unknown conversation.
  - Checked for and cleaned accidental artifacts — confirmed none tracked via `git status --ignored`.
  - Frontend intentionally not touched — coaching is genuinely new screen real estate with no existing mock/type/design to slot into, unlike Phase 9's near-perfect type fit; building UI now would mean guessing at unspecified design, against this phase's explicit rule not to fabricate requirements. Recorded in KNOWN_ISSUES.md for your review. `npm run build` re-verified clean as a regression check only.

**In Progress:** Awaiting your review of Phase 10.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin Phase 11 — Targeted Drills (generating focused practice scenarios from a rep's weakest competency, per Phase 10's priority pick — explicitly out of Phase 10's own boundary, which produced coaching text only, no drill generation, no reassessment loop, no adaptive difficulty).

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- Coaching has no frontend at all yet — API-only. See KNOWN_ISSUES.md and DECISIONS.md, Phase 10; needs an explicit design decision from you, not a guess.
- Phase 9 frontend Result integration not visually screenshot-verified in an actual browser this environment (unchanged from Phase 9).
- Phase 5 and Phase 7 frontend integration still carry the same pre-existing, unresolved visual-verification gap (unchanged).
- No scripted buyer opening line — unchanged, pre-existing (Phase 7 decision, still under your review).

**Known P3:**
- Coaching's priority pick carries no cross-competency causal reasoning (e.g., "weak closing traced back to weak discovery") — correctly scoped out per MASTER_PROMPT.md's "must not claim causality without evidence," since no `skill_graph_edges` exist yet. Owner: Phase 14.
- Coaching session does not auto-regenerate if readiness/evaluation ever changes after the fact — deliberate, same posture as readiness's identical decision. Owner: revisit only if a future phase adds re-computation.
- `AT_RISK_MARGIN = 10` is a placeholder judgment call, not calibrated against real transcripts. Owner: Phase 15.
- Readiness verdict does not auto-recompute if evaluation scores ever change after the fact — deliberate. Owner: revisit only if needed.
- Rejected (hallucinated/ungrounded) evidence candidates are silently dropped, not logged anywhere. Owner: Phase 15/18.
- `buyer_state_history` unbounded growth. Owner: Phase 20/21.
- Dev-mode auto schema creation needs an explicit production guard. Owner: Phase 21.
- MVP scenario seeding rides the same dev-only guard. Owner: Phase 21.
- `AnthropicProvider` still never exercised against the real Anthropic API for any module. Owner: final integration.
- Turn-submission responses include full message history on every turn — irrelevant at MVP scale.
- MVP is single-user via a synthetic default user — intentional, `user_id` FK already in place for Milestone 3.

**Technical Debt:** Same as before, plus the P3 items above.
**Last Successful Test:** `pytest -v` (backend) — 167 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors, unaffected (no frontend files changed this phase). `alembic upgrade head` — clean against a fresh DB, both migrations apply in order, all 12 tables present. Live `uvicorn` smoke test confirmed correct request/response behavior end to end, including graceful degradation.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 10.
