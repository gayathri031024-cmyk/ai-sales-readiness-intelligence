# TEST_STATUS.md

## Backend

| Test | Expected Result | Actual Result | Status | Phase |
|---|---|---|---|---|
| `test_root_responds` | GET `/` returns 200 with app name in message | 200, message contains app name | PASS | 3 |
| `test_health_reports_ok_and_db_connectivity` | GET `/health` returns `status: ok`, `database: ok`, no error | 200, all fields as expected | PASS | 3 |

Run with: `cd backend && python -m pytest -v`

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
