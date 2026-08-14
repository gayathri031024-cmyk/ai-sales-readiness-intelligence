# TEST_STATUS.md

## Backend

| Test | Expected Result | Actual Result | Status | Phase |
|---|---|---|---|---|
| `test_root_responds` | GET `/` returns 200 with app name in message | 200, message contains app name | PASS | 3 |
| `test_health_reports_ok_and_db_connectivity` | GET `/health` returns `status: ok`, `database: ok`, no error | 200, all fields as expected | PASS | 3 |
| `test_list_scenarios_returns_the_mvp_scenario` | GET `/scenarios` returns exactly 1 scenario matching Phase 0 spec | 200, 1 scenario, correct title/persona/difficulty/max_turns | PASS | 5 |
| `test_get_scenario_detail_includes_all_three_mvp_thresholds` | GET `/scenarios/{id}` returns thresholds for all 3 MVP competencies, objection_handling = 70 | 200, all 3 keys present, correct min_score | PASS | 5 |
| `test_get_scenario_404_for_unknown_id` | GET `/scenarios/does-not-exist` returns 404 | 404 | PASS | 5 |
| `test_buyer_hidden_state_never_appears_in_scenario_responses` | `base_state` never present in any scenario API response | Confirmed absent | PASS | 5 |
| `test_seed_mvp_scenario_is_idempotent` | Calling `seed_mvp_scenario` twice against a fresh DB creates exactly 1 scenario row | 1 row after 2 calls | PASS | 5 |

Run with: `cd backend && python -m pytest -v` — **7 passed** (verified fresh, `dev.db` removed first).

## Manual Verification (Phase 3)

| Check | Result |
|---|---|
| `alembic upgrade head` applies cleanly against fresh SQLite DB | ✅ 11 tables created, matching `DATA_MODEL.md` exactly |
| `alembic revision --autogenerate` detects all models correctly | ✅ all 11 tables detected on first run, no manual edits needed |
| Backend boots via `uvicorn` and serves real HTTP traffic (not just TestClient) | ✅ verified via curl against a live running server |
| Frontend `npm run build` completes (type-check + bundle) | ✅ built in ~450ms, no TS errors |
| Frontend dev server `/api` proxy reaches live backend | ✅ `curl http://127.0.0.1:5173/api/health` returned a valid response from the real backend process |

## Regression Suite

Not yet applicable — Phase 3 is the first phase with code. Regression testing becomes meaningful starting Phase 4.

## Frontend

No automated frontend tests yet (no real UI logic exists — Phase 3's App.tsx is a placeholder health check only). Test setup (Vitest + React Testing Library) to be added when Phase 4 introduces actual screens with logic worth testing.

## Manual Verification (Phase 4)

| Check | Result |
|---|---|
| `npm run build` (type-check + bundle) after all 3 screens added | ✅ 0 type errors |
| Screens rendered and screenshotted via Playwright against the production build | ✅ Start Scenario, Conversation (initial + after exchange), Result all captured and visually reviewed |
| Turn indexing consistency between mock conversation and mock evidence citations | ❌ found off-by-one on first pass → ✅ fixed and re-verified via screenshot |
| Backend regression (`pytest -v`) still passes after frontend-only changes | ✅ 2 passed |

Automated frontend tests (Vitest + RTL) still not yet added — first real candidates once Phase 5+ replaces mock data with real API calls and there's actual client-side logic (loading/error states, retries) worth unit testing.

## Manual Verification (Phase 5)

| Check | Result |
|---|---|
| `pytest -v` (backend, fresh `dev.db`) | ✅ 7 passed |
| `npm run build` (frontend, type-check + bundle) after wiring real scenario fetch | ✅ 0 type errors |
| Seed idempotency across two full app lifespans against the same on-disk SQLite file (not just the in-memory unit test) | ✅ 1 scenario after both startups |
| Live server manually curled (`uvicorn` + `curl /scenarios`) | ✅ correct real data returned, once, before the sandbox reclaimed the background process |
| Frontend dev server rendering the real scenario end-to-end, screenshotted (matching the Phase 3/4 verification bar) | ❌ **not completed** — background processes (uvicorn + vite dev server) were repeatedly killed by this sandbox between tool calls before a screenshot could be captured. This is an environment limitation, not a code issue; the backend contract is verified via automated tests + one successful manual curl, and the frontend fetch/adapter logic type-checks against that exact contract. **You should do one manual pass locally** (`uvicorn` in one terminal, `npm run dev` in another) to visually confirm the Start Scenario screen renders the live "Enterprise CFO — Price Objection" data before marking this checkpoint PASSED. |

## Regression Suite (Phase 5)

| Check | Result |
|---|---|
| Phase 3 backend tests (`test_health.py`) | ✅ still pass, unaffected |
| Phase 4 frontend build | ✅ still builds clean after mock removal + real fetch wiring |
