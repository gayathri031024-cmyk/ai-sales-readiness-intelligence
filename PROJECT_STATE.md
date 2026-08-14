# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 5 — Scenario Engine
**Current Checkpoint:** Phase 5 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED)

**Current Objective:** Get sign-off that the Scenario Engine is right — real seeded scenario data, the read API, and the frontend wired to consume it — before starting Phase 6 (Adaptive AI Buyer), which is where the first real LLM call enters the system.

**Completed Work:**
- Phases 0–4 approved (see CHANGELOG.md for detail)
- Phase 5 Scenario Engine built and verified by automated test:
  - `seed_mvp_scenario()` — idempotent seed of the single MVP scenario (Enterprise CFO — Price Objection), 3 competencies (Discovery/Objection Handling/Closing), and scenario-specific thresholds (60/70/65, rationale in DECISIONS.md)
  - `GET /scenarios`, `GET /scenarios/{id}` — thin router, service layer, and independent Pydantic response schemas (not the raw ORM models)
  - 5 new backend tests (7 total, all passing): list/detail happy paths, 404, a regression guard that buyer hidden state never leaks into a scenario response, and seed idempotency (verified both as an in-memory unit test and across two full app lifespans against the same on-disk SQLite file)
  - Frontend: `src/api/scenario.ts` fetches and adapts real backend data (snake_case → camelCase); `App.tsx` now fetches on mount with loading/error states; `StartScenario` renders real data; `src/mock/scenario.ts` deleted
  - `npm run build` — clean, 0 type errors, after the mock removal

**In Progress:** Awaiting your review of Phase 5 — **specifically the one manual verification step below that I could not complete in this environment.**

**Next Action:** Run the backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev`) locally, confirm the Start Scenario screen shows the real "Enterprise CFO — Price Objection" data (not blank, not an error state), then say `CHECKPOINT PASSED` to begin Phase 6 — Adaptive AI Buyer (first phase requiring a real LLM API key).

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- Conversation end-condition thresholds (turn limit / patience threshold / explicit close) not yet concretely specified — deferred to Phase 5/6 (still applies, now owned by Phase 6 since Phase 5 didn't touch conversation logic).
- Phase 5 frontend integration not visually verified end-to-end in this sandbox (background dev processes were repeatedly killed between tool calls before a screenshot could be captured) — full detail in KNOWN_ISSUES.md. Automated backend tests + a clean frontend type-check both pass; only the live visual pass is outstanding.

**Known P3:**
- `buyer_state_history` unbounded growth (Phase 20/21).
- Dev-mode auto schema creation needs an explicit production guard (Phase 21).
- MVP scenario seeding rides the same dev-only guard, same owner (Phase 21) — isolated in `scenario/service.py` so this is a mechanism swap, not a logic rewrite, when that phase arrives.
- Mock data in `src/mock/` (buyer.ts, readiness.ts) still in use for Conversation/Result screens — will be removed screen-by-screen as Phases 6/8/9 land, same as `scenario.ts` was this phase.

**Technical Debt:** Same as before, plus: seed-via-lifespan (see P3 above).
**Last Successful Test:** `pytest -v` (backend) — 7 passed, run fresh with `dev.db` removed first. `npm run build` (frontend) — clean, 0 type errors.
**Current Blockers:** Waiting on your local visual verification + Phase 5 approval.
