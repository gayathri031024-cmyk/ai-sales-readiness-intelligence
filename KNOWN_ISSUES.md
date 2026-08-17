# KNOWN_ISSUES.md

Classify: P0 — Critical | P1 — Important | P2 — Improvement | P3 — Optional
Remove an issue only after it's actually fixed and verified — don't just delete it because a phase ended.

## Open

**P2 — `Result` screen still renders Phase 4 mock data; not wired to real Phase 8 evaluation data**
`frontend/src/types.ts`'s `ReadinessResult` bundles Phase 8's evaluation data (`evaluations`) together with Phase 9's readiness verdict (`verdict`/`reasoning`) in one type, and `screens/Result.tsx` renders both together (each competency card compares `score` against `requiredMinScore`, which is itself Phase 9 readiness-threshold logic). Wiring the screen to real data now would mean either fabricating a placeholder verdict (a Phase 9 concept explicitly out of this phase's boundary) or splitting the type/screen ahead of Phase 9 actually needing that split. The real evaluation pipeline is fully built, tested, and reachable via `POST`/`GET /conversations/{id}/evaluate(ion)` — this is a frontend-wiring gap only, not a backend gap. See DECISIONS.md, Phase 8.
Origin: Phase 8. Owner: Phase 9 (wire `Result` to both real evaluation and real readiness data together).

**P2 — Phase 5 frontend integration not visually verified end-to-end in this environment**
Backend contract is covered by 5 passing tests plus one successful manual `curl` against a live server; frontend build type-checks clean against that exact contract. But unlike Phase 3/4, no Playwright screenshot of the real Start Scenario screen rendering live backend data exists — background dev processes were repeatedly reclaimed by the sandbox before a screenshot could be taken. Needs one manual local verification pass (`uvicorn` + `npm run dev`, look at the browser) before treating Phase 5 as fully verified to the project's own established bar.
Origin: Phase 5. Owner: you, before `CHECKPOINT PASSED`.

**P2 — Phase 7 frontend conversation UI not visually verified end-to-end in this environment**
Same sandbox limitation as the Phase 5 item directly above: `npm run build` type-checks clean, and the backend contract it's built against has 27 passing automated tests plus a live-server manual `curl` smoke test (start conversation, submit a turn, confirm graceful degradation and correct persistence with no `LLM_API_KEY` set). But no Playwright screenshot of the actual Conversation screen rendering a live multi-turn exchange in the browser exists — background `uvicorn`/`vite dev` processes are reclaimed between tool calls before a screenshot can be captured. Needs one manual local pass (`uvicorn` in one terminal, `npm run dev` in another, click through Start → Conversation) before treating Phase 7's frontend as fully verified to the project's own established bar.
Origin: Phase 7. Owner: you, before `CHECKPOINT PASSED`.

**P2 — No scripted buyer opening line; the rep now always speaks first**
The Phase 4 mock UI opened every conversation with a canned buyer objection line. Phase 7's real buyer engine (`run_buyer_turn`) always classifies a rep message before replying, so there's no code path to generate an opening line without inventing a second, ungated reply path — ruled out by this phase's PHASE BOUNDARY. The live Conversation screen now opens on an empty transcript with a UI hint instead. This is a product-UX decision worth your explicit review (see DECISIONS.md, Phase 7), not an oversight.
Origin: Phase 7. Owner: you, review before `CHECKPOINT PASSED`; implementation owner if changed would be a later phase or a Phase 7 follow-up commit.

**P3 — Turn-submission endpoint returns the full conversation payload, including full message history, on every turn**
Simpler frontend state model (see DECISIONS.md), but response payload size grows linearly with conversation length — irrelevant at MVP scale (max 12 turns) but worth a lighter-weight response shape if conversations ever get much longer.
Origin: Phase 7. Owner: revisit only if a later phase's real usage shows this mattering.

**P3 — `AnthropicProvider` untested against the real Anthropic API**
`AnthropicProvider` is implemented and structurally correct (lazy client construction, `LLMUnavailableError` on missing key, response parsing) but has never been exercised against a live API — no key has been provided per the project's explicit instruction not to require one. The Phase 7 conversation endpoints were smoke-tested live via `curl` against a real running server, but still without a real key configured (so the buyer engine's graceful-degradation path ran, not the live-model path). Needs one live smoke test once a real `LLM_API_KEY` is added.
Origin: Phase 6. Owner: final integration.

**P3 — `buyer_state_history` grows unbounded per conversation**
Fine at prototype scale; needs a retention/pruning policy before real deployment.
Origin: Phase 2. Owner: Phase 20/21.

**P3 — Dev-mode auto schema creation (`Base.metadata.create_all`) bypasses Alembic**
Convenient for local Phase 3 verification, but means dev and migration-managed schemas could silently drift if models change without a new migration. Acceptable now; must be removed or guarded more strictly before Phase 21 (production relies exclusively on Alembic per `main.py` comment).
Origin: Phase 3. Owner: Phase 21.

**P3 — MVP scenario seed data rides the same dev-only lifespan guard as schema auto-creation**
`seed_mvp_scenario()` is idempotent and correct for a single hardcoded MVP scenario, but is not how seeding should work once real scenario authoring exists — no proper seed migration path exists yet. Same bucket/owner as the item above; `seed_mvp_scenario()` is isolated in `scenario/service.py` specifically so a real Phase 21 migration can call it without touching its logic.
Origin: Phase 5. Owner: Phase 21.

**P3 — Rejected (hallucinated/ungrounded) evidence candidates are silently dropped, not logged anywhere**
`evaluation/verification.py::verify_evidence` correctly refuses to persist a candidate that fails grounding, but keeps no record of what was rejected or why. Fine for MVP correctness (the invariant this phase exists to build — "only grounded evidence persists" — holds either way), but Phase 15 (Stress Testing) / Phase 18 (AI Evaluation Benchmark) will likely want a rejection log to measure how often extraction actually hallucinates against a real model, not just prove the system survives it when it does.
Origin: Phase 8. Owner: Phase 15/18.

**P3 — MVP is single-user via a synthetic default user, no real auth**
`conversation.service.get_or_create_default_user` attributes every conversation to the same synthetic user regardless of who is actually using it. Intentional and explicitly deferred per ARCHITECTURE.md §8 (multi-user auth is Milestone 3 scope); the `user_id` FK already exists specifically so this doesn't require a schema change later.
Origin: Phase 7. Owner: Milestone 3 / whichever phase adds real auth.

## Resolved

**P2 — Conversation end-condition thresholds undefined** *(resolved Phase 7)*
Turn-limit end condition uses `scenario.max_turns` (already in the data model). Patience-exhausted end condition uses the `BuyerState` schema's own clamp floor (`patience <= 0`). Explicit-close is a dedicated `POST /conversations/{id}/close` endpoint. See DECISIONS.md, Phase 7, for the reasoning behind each choice.

**P2 — Buyer module has no persistence or API route yet** *(resolved Phase 7)*
`app/conversation/service.py` now loads persisted `current_buyer_state` from the DB, calls the unchanged `buyer/service.run_buyer_turn()` once per turn, and persists the result (`Conversation.current_buyer_state`, a new `Message` pair, and a `BuyerStateHistory` row) inside a single DB transaction per turn. Wired to `POST /conversations/{id}/turns` in `app/api/routes/conversation.py`.

