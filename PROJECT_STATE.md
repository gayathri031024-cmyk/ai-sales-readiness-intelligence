# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 9 — Readiness Engine
**Current Checkpoint:** Phase 9 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED); Phase 6 — Adaptive AI Buyer (PASSED); Phase 7 — Conversation Engine (PASSED); Phase 8 — Evaluation Engine (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 8`)

**Current Objective:** Get sign-off that the Readiness Engine correctly turns Phase 8's persisted competency scores into a deterministic READY/NOT_READY/AT_RISK verdict against the scenario's real thresholds — with zero LLM calls anywhere in the module, correct idempotency, and the frontend Result screen now consuming real data end to end.

**Completed Work:**
- Phases 0–8 approved (see CHANGELOG.md for detail)
- Phase 9 Readiness Engine built and verified by automated test + live manual smoke test + live proxy integration check:
  - Verified the Phase 8 baseline first (120/120 tests, clean git state)
  - Found `app/readiness/decision.py`, `schemas.py`, `service.py` already present, uncommitted, at the start of this phase — origin unknown, not something written earlier in this session or present when Phase 8 inspected the same directory. Treated as an unverified discrepancy per the standing working rule ("do not trust... assumptions"): read against the actual DB schema (`db/models.py`) and every relevant control document (ARCHITECTURE.md §3, MASTER_PROMPT.md, DATA_MODEL.md, `scenario/service.py`'s real seeded thresholds) — structurally consistent with all of them — then proven correct by writing and running 24 real tests against it, not accepted on inspection alone. One real bug was found and fixed in the process, but it was in the test fixture, not the found code. Full account in DECISIONS.md, Phase 9.
  - `app/readiness/decision.py` — pure, deterministic `decide_readiness()`: READY if every competency clears its threshold; NOT_READY or AT_RISK depending on whether the worst gap among failing competencies is within `AT_RISK_MARGIN = 10` points or beyond it; reasoning text names every failing competency by score and required minimum. Zero LLM calls, test-enforced.
  - `app/readiness/service.py` — `compute_and_persist_readiness` (idempotent — a persisted verdict is treated as authoritative, never silently recomputed), `get_readiness` (fetch-only), `get_conversation_result` (combined evaluations+thresholds+verdict shape for the frontend). Persists `thresholds_snapshot` (actual scenario thresholds at computation time) on every row. Deliberately never triggers Phase 8's evaluation step itself, even lazily.
  - Built the missing API layer: `app/api/routes/readiness.py` (`POST`/`GET /conversations/{id}/readiness`, `GET /conversations/{id}/result`), wired into `main.py`. 409 if evaluation hasn't run yet; 404 for unknown conversations/not-yet-computed readiness.
  - 24 new backend tests (144 total, all passing) — `decide_readiness` boundary logic at the unit level, full API-level READY/NOT_READY/AT_RISK coverage, idempotency (zero duplicate rows, verdict never drifts), the combined `/result` endpoint's lazy-compute behavior, hidden-state protection, zero-LLM-call guarantee, and `thresholds_snapshot` persistence verified against real scenario data
  - No new migration needed — confirmed via `alembic upgrade head` against a fresh DB (`readiness_results` already existed from Phase 2/3)
  - Frontend wired to real data: new `frontend/src/api/readiness.ts` sequences Phase 8's evaluation trigger and Phase 9's result fetch (the backend deliberately never chains them); `App.tsx`/`Conversation.tsx` now thread the real conversation id through instead of mock data or a raw transcript; deleted the now-orphaned `mock/readiness.ts`. `Result.tsx`/`types.ts` needed **no changes** — the Phase 4 mock-data types already matched the real API shape field-for-field.
  - Live manual verification: direct backend `curl` smoke test (create → close → evaluate → readiness → result, correct NOT_READY verdict for a zero-evidence conversation; 409 precondition confirmed), plus — one layer deeper than any prior phase — a live integration check through the **actual Vite dev-server proxy** (`uvicorn` + `vite dev` running together), confirming the exact request sequence `api/readiness.ts` performs all returns correct data through the real proxy path a browser would use. Rendered browser DOM/visual output was not captured — see Known P2 below.
  - Checked for and confirmed no accidental artifacts (`.env`, `dev.db`, `__pycache__`, `.pytest_cache`) are tracked in git — all correctly excluded by the existing `.gitignore`.

**In Progress:** Awaiting your review of Phase 9.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin Phase 10 — AI Coach (the first phase of Milestone 2: root-cause diagnosis and personalized coaching built from Phase 8's evidence + Phase 9's verdict — explicitly out of Phase 9's own boundary, which produced the verdict only, no coaching, no targeted drills, no adaptive difficulty).

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- Phase 9 frontend Result integration not visually screenshot-verified in an actual browser this environment — same sandbox limitation as Phase 5/7, though this phase went one step further than either (full request chain verified live through the real Vite proxy, not just a clean `npm run build`). See KNOWN_ISSUES.md.
- Phase 5 and Phase 7 frontend integration still carry the same pre-existing, unresolved visual-verification gap (unchanged this phase).
- No scripted buyer opening line — unchanged, pre-existing (Phase 7 decision, still under your review).

**Known P3:**
- `AT_RISK_MARGIN = 10` is a placeholder judgment call, not calibrated against real transcripts — same category as the scenario threshold values themselves. Revisit trigger: Phase 15.
- Readiness verdict does not auto-recompute if evaluation scores ever change after the fact — deliberate (see DECISIONS.md, Phase 9), revisit only if a future phase adds evaluation re-computation.
- Rejected (hallucinated/ungrounded) evidence candidates are silently dropped, not logged anywhere — Phase 15/18 owner.
- `buyer_state_history` unbounded growth (Phase 20/21).
- Dev-mode auto schema creation needs an explicit production guard (Phase 21).
- MVP scenario seeding rides the same dev-only guard (Phase 21).
- `AnthropicProvider` still never exercised against the real Anthropic API for any module — needs one live smoke test once a real `LLM_API_KEY` is added.
- Turn-submission responses include the full message history on every turn — irrelevant at MVP scale.
- MVP is single-user via a synthetic default user — intentional, `user_id` FK already in place for Milestone 3.

**Technical Debt:** Same as before, plus the P3 items above.
**Last Successful Test:** `pytest -v` (backend) — 144 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors, run fresh. `alembic upgrade head` — clean against a fresh DB, all 11 tables present. Live `uvicorn` smoke test and live Vite-proxy integration check both confirmed correct request/response behavior end to end.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 9.
