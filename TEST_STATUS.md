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

## Backend (Phase 6 additions)

| Test file | Covers | Status | Phase |
|---|---|---|---|
| `test_buyer_state.py` (7 tests) | State bounds, clamping (above/below/at edges), pure `apply_deltas`, exactly 4 documented dimensions (no scope creep) | PASS | 6 |
| `test_buyer_rules.py` (10 tests) | Every `RepBehavior` label has a rule, determinism, directionally sensible deltas, injection penalty, boundary clamping under repeated updates | PASS | 6 |
| `test_llm_provider.py` (12 tests) | `MockLLMProvider` queued/default/call-recording behavior, `AnthropicProvider` fails without a key without ever calling the network, structured-output parse/validate/retry-once/second-failure/JSON-extraction-from-prose | PASS | 6 |
| `test_buyer_classification.py` (7 tests) | Valid classification, degrade-to-UNCLEAR on unavailability and on repeated malformed output, retry-then-recover, out-of-range value rejected, rep message delimited, full label coverage | PASS | 6 |
| `test_buyer_response.py` (9 tests) | Healthy reply passthrough, fallback on unavailability/empty response, leak scrubber catches numeric/AI-disclosure/system-prompt leaks, explicit false-positive guard for ordinary business language, message delimiting, no raw numeric state in the system prompt | PASS | 6 |
| `test_buyer_prompt_injection.py` (5 tests) | End-to-end via `run_buyer_turn`: injection messages classified correctly and penalize trust/patience, scrubber catches a hypothetical future model leak of state or system prompt, in-character behavior when the model behaves correctly, no state object leaking into reply text | PASS | 6 |
| `test_buyer_graph.py` (7 tests) | Graph compiles, singleton caching, full happy-path turn, state purity (original object unmutated), full degradation with no crash, turn_index wiring, node ordering (reply reflects post-update state, not pre-update) | PASS | 6 |
| `test_buyer_state_exposure.py` (3 tests) | Hidden-state regression guard on the buyer-turn output specifically (complements the Phase 5 scenario-API guard): no field name, no exact seeded numeric value, structural type-level separation between reply and state | PASS | 6 |

Run with: `cd backend && python -m pytest -v` — **67 passed** (verified fresh, `dev.db` removed, `LLM_API_KEY`/`LLM_MODEL`/`ANTHROPIC_API_KEY` all unset — zero network calls, zero API cost).

## Manual Verification (Phase 6)

| Check | Result |
|---|---|
| Full suite passes with zero LLM-related env vars set | ✅ 67 passed |
| `npm run build` (frontend, untouched by this phase — regression check only) | ✅ 0 type errors |
| No `.env` tracked in git; no API key present in any tracked file | ✅ confirmed via `git ls-files` and manual review |
| `AnthropicProvider` against a real API key | ❌ **not done, by design** — no key provided this phase per your explicit instruction; tracked as P3 in `KNOWN_ISSUES.md`, owner: final integration |

## Regression Suite (Phase 6)

| Check | Result |
|---|---|
| Phase 5 backend tests (`test_scenario.py`, `test_health.py` — 7 tests) | ✅ still pass, unchanged, now part of the 67 |
| Frontend build | ✅ still builds clean — Phase 6 made no frontend changes |

## Backend (Phase 7 additions)

| Test file | Covers | Status | Phase |
|---|---|---|---|
| `test_conversation.py` (27 tests) | Conversation creation (valid/invalid scenario, initial state matches persona `base_state`, starts `in_progress`); retrieval (public shape, 404 for unknown id, hidden state absent from JSON); turn submission (message/reply persisted, turn count increments, hidden state updated in DB, 404 for unknown conversation); **multi-turn persistence** (turn 2 provably builds on turn 1's persisted state rather than resetting to the initial state — asserted against exact expected deltas from `buyer/rules.py`, and against `buyer_state_history` rows directly); message history ordering with no duplication; terminal conditions (turn-limit completion, patience-exhausted completion, explicit close, idempotent re-close, terminal conversation rejects further turns with 409 and does not mutate state or append messages); hidden-state protection (no `trust`/`patience`/`budget_sensitivity`/`interest`/`current_buyer_state`/`classified_intent` in any response, no system-prompt/rationale/classification leakage); failure behavior (graceful degradation with no `LLM_API_KEY` set still returns a valid conversation and non-empty fallback reply, invalid conversation id returns 404 not 500, completed conversation returns 409 not 500, empty message returns 422) | PASS | 7 |

Run with: `cd backend && python -m pytest -v` — **94 passed** (67 Phase 0–6 + 27 Phase 7, verified fresh with `dev.db` removed and all LLM-related env vars unset — zero network calls, zero API cost).

## Manual Verification (Phase 7)

| Check | Result |
|---|---|
| Full suite passes with zero LLM-related env vars set | ✅ 94 passed |
| `alembic upgrade head` against a fresh SQLite DB | ✅ all 11 tables created (schema already covered `conversations`/`messages`/`buyer_state_history` since Phase 2/3 — no new migration was needed for Phase 7) |
| Fresh-DB migration followed by `seed_mvp_scenario()` twice | ✅ 1 scenario row, unaffected by the (absent) schema change |
| Backend boots via `uvicorn` and serves real HTTP traffic (not just `TestClient`) | ✅ `curl /health` → `status: ok`; `curl -X POST /conversations` → real conversation created with correct initial public shape and no hidden-state fields |
| Live turn submission against a real running server, no `LLM_API_KEY` set | ✅ `curl -X POST /conversations/{id}/turns` → graceful-degradation fallback reply returned, both messages persisted, `turn_count` incremented correctly |
| Live 404 handling against a real running server | ✅ `curl /conversations/does-not-exist` → `{"detail": "Conversation not found"}` |
| `npm run build` (frontend, type-check + bundle) after wiring the real conversation API into the Conversation screen | ✅ 0 type errors |
| Frontend dev server rendering a live multi-turn conversation, screenshotted | ❌ **not completed** — same environment limitation as Phase 5's open item: background `uvicorn`/`vite dev` processes were reclaimed by this sandbox between tool calls before a screenshot could be captured. The backend contract is covered by 27 automated tests plus the live-server `curl` checks above, and the frontend's adapter/screen code type-checks against that exact contract. **You should do one manual local pass** (`uvicorn` in one terminal, `npm run dev` in another) to visually confirm Start → Conversation → sending a message → seeing a buyer reply, before marking this checkpoint PASSED. |

## Regression Suite (Phase 7)

| Check | Result |
|---|---|
| All Phase 0–6 backend tests (67) | ✅ still pass, unchanged, now part of the 94 |
| Frontend build | ✅ still builds clean — `types.ts` additions are additive; `Conversation.tsx` and `mock/buyer.ts` were the only files changed/removed, both explicitly in Phase 7's scope (mock buyer replacement) |

## Backend (Phase 8 additions)

| Test file | Covers | Status | Phase |
|---|---|---|---|
| `test_evaluation.py` (26 tests) | Evidence extraction (valid multi-competency extraction, schema-validation retry-once on an invalid `competency_key`, malformed-JSON retry); deterministic verification (grounded quote accepted, ungrounded/fabricated quote rejected, reference to a nonexistent turn rejected, quote attributed to a BUYER message rejected, whitespace/case-tolerant matching); competency scoring (LLM-assisted scoring from verified evidence only, deterministic no-evidence path with zero LLM calls, deterministic degraded-unavailable path distinguishable from the no-evidence path, leak-scrubber unit test); persistence (`Evaluation`+`Evidence` rows correctly linked via FK, exactly 3 rows per conversation always); retrieval (`GET` returns the persisted result, 404 before any evaluation exists, 404 for an unknown conversation); idempotency (repeat `POST .../evaluate` returns identical data with zero additional LLM calls and no duplicate rows); hidden-state/system-prompt/internal-reasoning protection (none of `trust`/`patience`/`budget_sensitivity`/`interest`/`current_buyer_state`/"system prompt"/"internal reasoning"/"chain of thought"/`classified_intent` ever appear in the response); public API schema shape; error handling (404 unknown conversation, 409 conversation not yet completed); empty-transcript behavior (zero-turn conversation evaluates fully deterministically with zero LLM calls); LLM-call ordering across the 3 MVP competencies | PASS | 8 |

Run with: `cd backend && python -m pytest -v` — **120 passed** (94 Phase 0–7 + 26 Phase 8, verified fresh with `dev.db` removed and all LLM-related env vars unset — zero network calls, zero API cost).

## Manual Verification (Phase 8)

| Check | Result |
|---|---|
| Full suite passes with zero LLM-related env vars set | ✅ 120 passed |
| `alembic upgrade head` against a fresh SQLite DB | ✅ all 11 tables created (schema already covered `evaluations`/`evidence`/`competencies` since Phase 2/3 — no new migration was needed for Phase 8) |
| Backend boots via `uvicorn` and serves real HTTP traffic (not just `TestClient`) | ✅ `curl /health` → `status: ok` |
| Live end-to-end smoke test against a real running server, no `LLM_API_KEY` set | ✅ create conversation → close with zero turns → `POST /conversations/{id}/evaluate` → all 3 MVP competencies persisted with deterministic score-0 "no evidence observed" results (correct graceful-degradation behavior for an empty transcript) → `GET /conversations/{id}/evaluation` returns the identical persisted result → `POST` against an unknown conversation id returns 404 |
| `npm run build` (frontend, untouched by this phase — regression check only; see DECISIONS.md/KNOWN_ISSUES.md for why `Result` isn't wired yet) | ✅ 0 type errors |
| No `.env` tracked in git; no API key present in any tracked file | ✅ confirmed via `git ls-files` and manual review |

## Regression Suite (Phase 8)

| Check | Result |
|---|---|
| All Phase 0–7 backend tests (94) | ✅ still pass, unchanged, now part of the 120 |
| Frontend build | ✅ still builds clean — no frontend files were touched this phase |

## Backend (Phase 9 additions)

| Test file | Covers | Status | Phase |
|---|---|---|---|
| `test_readiness.py` (24 tests) | `decide_readiness` at the unit level (no DB/HTTP): all-pass → READY, score exactly equal to threshold still passes, a gap of exactly `AT_RISK_MARGIN` (10) → AT_RISK, a gap of `AT_RISK_MARGIN + 1` → NOT_READY, reasoning text names every failing competency by display name and required minimum, raises on an empty competency-results list, `CompetencyResult.gap`/`.passed` boundary math; full API-level readiness computation (READY when all competencies clear their threshold, NOT_READY on a wide miss, AT_RISK on a narrow miss); precondition enforcement (`POST .../readiness` before evaluation → 409, unknown conversation → 404 on all three endpoints); retrieval (`GET .../readiness` 404 before computed, returns identical persisted verdict after); idempotency (repeat `POST .../readiness` returns identical data, exactly one `readiness_results` row, verdict never drifts); the combined `GET .../result` endpoint (lazily computes-and-persists readiness if not yet explicitly triggered, includes `required_min_score` per competency alongside its scenario threshold, 404 if evaluation hasn't run yet, public schema shape); hidden-state protection (no `trust`/`patience`/`budget_sensitivity`/`interest`/`current_buyer_state` in either response); zero-LLM-call guarantee (`mock_provider.calls` count unchanged before/after both readiness endpoints); threshold-snapshot persistence (`readiness_results.thresholds_snapshot` matches the scenario's actual seeded thresholds `{discovery: 60, objection_handling: 70, closing: 65}` at computation time) | PASS | 9 |

Run with: `cd backend && python -m pytest -v` — **144 passed** (120 Phase 0–8 + 24 Phase 9, verified fresh with `dev.db` removed and all LLM-related env vars unset — zero network calls, zero API cost).

## Manual Verification (Phase 9)

| Check | Result |
|---|---|
| Full suite passes with zero LLM-related env vars set | ✅ 144 passed |
| `alembic upgrade head` against a fresh SQLite DB | ✅ all 11 tables created (`readiness_results` already existed since Phase 2/3 — no new migration was needed for Phase 9 either) |
| Backend boots via `uvicorn` and serves real HTTP traffic | ✅ `curl /health` → `status: ok`; full manual sequence (create → close zero-turn conversation → evaluate → readiness → result) against a real running server returned the correct deterministic NOT_READY verdict for an evidence-free conversation |
| `npm run build` (frontend) | ✅ 0 type errors |
| Live integration through the actual Vite dev-server proxy (not just direct backend `curl`) | ✅ started `uvicorn` on :8000 and `vite dev` on :5173 together; `GET /api/scenarios` → `POST /api/conversations` → `POST /api/conversations/{id}/close` → `POST /api/conversations/{id}/evaluate` → `GET /api/conversations/{id}/result` — the exact sequence `frontend/src/api/readiness.ts` performs — all returned correct data through the proxy; main page (`GET /`) returned 200. Rendered browser DOM/visual output was NOT captured (see KNOWN_ISSUES.md — same sandbox limitation as Phase 5/7, though this phase verified one layer deeper than either of those did) |
| No `.env` tracked in git; no accidental artifacts (`dev.db`, `__pycache__`, `.pytest_cache`) committed | ✅ confirmed via `git status --ignored` — all present locally but correctly excluded by `.gitignore`, none tracked |

## Regression Suite (Phase 9)

| Check | Result |
|---|---|
| All Phase 0–8 backend tests (120) | ✅ still pass, unchanged, now part of the 144 |
| Frontend build | ✅ still builds clean — `Result.tsx`/`types.ts` needed no changes; `App.tsx`/`Conversation.tsx` changes type-check correctly against the real API contract |

## Backend (Phase 10 additions)

| Test file | Covers | Status | Phase |
|---|---|---|---|
| `test_coaching.py` (23 tests) | `pick_priority` at the unit level (no DB/HTTP/LLM): worst-gap pick when something fails, narrowest-margin pick when everything passes, tie-breaking by fixed MVP competency order, raises on an empty result list; `verify_coaching_points` at the unit level: accepts a valid evidence reference, rejects a fabricated evidence id, rejects a real evidence id cited under the wrong competency, rejects a competency not evaluated this conversation, allows a null evidence id through unchanged; full API-level coaching pipeline (priority matches the worst failing competency end to end, a grounded point with a real evidence id persists correctly, a point citing a fabricated evidence id never reaches the API response); graceful degradation (full LLM outage falls back to a deterministic summary built from the same priority data — verified the priority itself is still correct even with the LLM fully down; malformed-JSON retry-then-succeed); precondition/error handling (`POST .../coaching` before readiness → 409, unknown conversation → 404 on both endpoints, `GET .../coaching` 404 before generated); idempotency (repeat `POST .../coaching` returns identical data, exactly one `coaching_sessions` row, zero additional LLM calls); hidden-state/system-prompt/internal-reasoning protection; public API schema shape | PASS | 10 |

Run with: `cd backend && python -m pytest -v` — **167 passed** (144 Phase 0–9 + 23 Phase 10, verified fresh with `dev.db` removed and all LLM-related env vars unset — zero network calls, zero API cost).

## Manual Verification (Phase 10)

| Check | Result |
|---|---|
| Full suite passes with zero LLM-related env vars set | ✅ 167 passed |
| Found pre-existing, uncommitted `coaching/` code stashed and the actual Phase 9 baseline (144 tests) re-verified in isolation first, before restoring and evaluating the found work on its own merits | ✅ confirmed 144/144 clean at commit `b2edc18` with the found work set aside |
| `alembic upgrade head` against a fresh SQLite DB | ✅ both migrations apply in order (`9f7e1a8e08c5` → `c054f45455ae`); all 12 tables present, `coaching_sessions` schema matches the ORM model exactly (verified column-by-column via `PRAGMA table_info`) |
| Backend boots via `uvicorn` and serves real HTTP traffic | ✅ `curl /health` → ok; full manual sequence (create → close → coaching-before-readiness → 409 → evaluate → readiness → coaching → correct deterministic fallback with no `LLM_API_KEY` set → GET returns identical data → 404 for an unknown conversation) all confirmed correct against a real running server |
| `npm run build` (frontend, untouched this phase — regression check only) | ✅ 0 type errors |
| No `.env` tracked in git; no accidental artifacts (`dev.db`, `__pycache__`, `.pytest_cache`) committed | ✅ confirmed via `git status --ignored` |

## Regression Suite (Phase 10)

| Check | Result |
|---|---|
| All Phase 0–9 backend tests (144) | ✅ still pass, unchanged, now part of the 167 |
| Frontend build | ✅ still builds clean — no frontend files touched this phase (see KNOWN_ISSUES.md) |
