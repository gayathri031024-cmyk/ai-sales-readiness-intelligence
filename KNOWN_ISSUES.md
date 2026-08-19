# KNOWN_ISSUES.md

Classify: P0 — Critical | P1 — Important | P2 — Improvement | P3 — Optional
Remove an issue only after it's actually fixed and verified — don't just delete it because a phase ended.

## Open

**P2 — Phase 5 frontend integration not visually verified end-to-end in this environment**
Backend contract is covered by 5 passing tests plus one successful manual `curl` against a live server; frontend build type-checks clean against that exact contract. But unlike Phase 3/4, no Playwright screenshot of the real Start Scenario screen rendering live backend data exists — background dev processes were repeatedly reclaimed by the sandbox before a screenshot could be taken. Needs one manual local verification pass (`uvicorn` + `npm run dev`, look at the browser) before treating Phase 5 as fully verified to the project's own established bar.
Origin: Phase 5. Owner: you, before `CHECKPOINT PASSED`.

**P2 — Phase 7 frontend conversation UI not visually verified end-to-end in this environment**
Same sandbox limitation as the Phase 5 item directly above: `npm run build` type-checks clean, and the backend contract it's built against has 27 passing automated tests plus a live-server manual `curl` smoke test (start conversation, submit a turn, confirm graceful degradation and correct persistence with no `LLM_API_KEY` set). But no Playwright screenshot of the actual Conversation screen rendering a live multi-turn exchange in the browser exists — background `uvicorn`/`vite dev` processes are reclaimed between tool calls before a screenshot can be captured. Needs one manual local pass (`uvicorn` in one terminal, `npm run dev` in another, click through Start → Conversation) before treating Phase 7's frontend as fully verified to the project's own established bar.
Origin: Phase 7. Owner: you, before `CHECKPOINT PASSED`.

**P2 — No scripted buyer opening line; the rep now always speaks first**
The Phase 4 mock UI opened every conversation with a canned buyer objection line. Phase 7's real buyer engine (`run_buyer_turn`) always classifies a rep message before replying, so there's no code path to generate an opening line without inventing a second, ungated reply path — ruled out by this phase's PHASE BOUNDARY. The live Conversation screen now opens on an empty transcript with a UI hint instead. This is a product-UX decision worth your explicit review (see DECISIONS.md, Phase 7), not an oversight.
Origin: Phase 7. Owner: you, review before `CHECKPOINT PASSED`; implementation owner if changed would be a later phase or a Phase 7 follow-up commit.

**P2 — Phase 9 frontend Result integration not visually screenshot-verified (browser) in this environment**
Same sandbox limitation as the Phase 5/7 items above — no Playwright screenshot of the actual `Result` screen rendering a real READY/AT_RISK/NOT_READY verdict in a browser exists. Unlike those two items, this phase did go one step further than a clean `npm run build`: the full request chain was verified live through the actual Vite dev-server proxy (not just direct backend `curl`) — `GET /api/scenarios` → `POST /api/conversations` → `POST /api/conversations/{id}/close` → `POST /api/conversations/{id}/evaluate` → `GET /api/conversations/{id}/result`, the exact sequence `frontend/src/api/readiness.ts` performs, all returning correct data through the proxy that a real browser would also go through. What's still unverified is purely the rendered DOM/visual output of `Result.tsx` against that data. Needs one manual local pass (`uvicorn` + `npm run dev`, click through Start → Conversation → Result in an actual browser) before treating Phase 9's frontend as fully verified to the project's own established bar.
Origin: Phase 9. Owner: you, before `CHECKPOINT PASSED`.

**P2 — Coaching has no frontend at all yet — API-only**
`POST`/`GET /conversations/{id}/coaching` are complete, tested (23 tests), and live-smoke-tested against a real running server, but nothing in `frontend/src` references coaching — no type, no adapter, no UI. Unlike Phase 9 (where the existing mock types already matched the real API shape with zero changes needed), a coaching UI would be genuinely new screen real estate with no existing mock/design to slot into, and no control document specifies what it should look like. Building one now would mean guessing at unspecified UI/UX scope — explicitly against this phase's rule 10 ("do not guess or fabricate requirements"). See DECISIONS.md, Phase 10.
Origin: Phase 10. Owner: you — either specify the coaching UI design for a follow-up commit, or explicitly defer it to a later phase.

**P2 — Drills have no frontend at all yet — API-only, same reasoning as coaching**
`POST`/`GET /conversations/{id}/drill` are complete, tested (16 tests), and live-smoke-tested against a real running server. A drill card would sit downstream of a coaching card that doesn't exist in the frontend yet — building drill UI first would mean building on top of nothing. See DECISIONS.md, Phase 11.
Origin: Phase 11. Owner: you — same call as the coaching item above, ideally decided together since they're the same unbuilt UI chain.

**P2 — The training loop's "reassessment" step is not implemented — "drill → practice → reassessment → competency achieved" stops after "drill" this phase**
`DATA_MODEL.md` lists `drills` and `reassessments` as two separate deferred tables. Phase 11 built the first; the second — linking a fresh practice conversation back to the specific drill it was practicing, then automatically comparing before/after evaluation scores to confirm the weakness was fixed — has zero column-level specification anywhere beyond the bare table name, and was not guessed at (rule 9 of this phase: do not guess missing requirements). A rep can already start a fresh practice conversation today using the drill's `practice_scenario_id` via the existing `POST /conversations` flow — what's missing is the system automatically recognizing that conversation *as* a reassessment of a specific drill. See DECISIONS.md, Phase 11.
Origin: Phase 11. Owner: a dedicated future phase — not the same concept as Phase 12 (Adaptive Difficulty), which is about difficulty scaling, not the reassessment link-back mechanism.

**P2 — "Targeted" drills currently target only the competency to focus on, not a distinct practice scenario**
The MVP has exactly one seeded scenario — there is no scenario library or authoring capability for a drill to select a *different* scenario from. `Drill.practice_scenario_id` is always identical to the origin conversation's own `scenario_id`; it exists now so a future multi-scenario phase can start varying it without a schema change, but currently carries no new information. See DECISIONS.md, Phase 11, for the full reasoning.
Origin: Phase 11. Owner: whichever future phase adds a scenario library.

**P2 — Adaptive difficulty has no frontend at all yet — API-only, same reasoning as coaching/drills**
`GET /conversations/{id}/difficulty-recommendation` is complete, tested (31 tests), and live-smoke-tested against a real running server, but nothing in `frontend/src` references it — no type, no adapter, no UI. No control document specifies what a difficulty-recommendation UI should look like, and it would sit downstream of the still-unbuilt coaching/drill UI chain. See DECISIONS.md, Phase 12.
Origin: Phase 12. Owner: you — same call as the coaching/drills items above, ideally decided together since they're the same unbuilt UI chain.

**P2 — Adaptive difficulty is advisory only against the MVP's single seeded scenario — there is no "easy" or "hard" scenario to actually route a rep to**
`recommend_difficulty` can correctly recommend `"easy"` or `"hard"` today (e.g., a NOT_READY verdict recommends stepping down from `"standard"` to `"easy"`), but the MVP has exactly one seeded scenario, always at `difficulty="standard"` (unchanged since Phase 5). The recommendation is honest, correct, and fully testable text describing what a rep *should* practice next — it does not (and, per this phase's strict boundaries, must not) fabricate a scenario library to route them to. Same honest scope gap `drills/generation.py`'s `practice_scenario_id` decision recorded in Phase 11 for an analogous reason. See DECISIONS.md, Phase 12.
Origin: Phase 12. Owner: whichever future phase adds a scenario library.

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

**P3 — `AT_RISK_MARGIN` (10 points) is a placeholder judgment call, not calibrated against real transcripts**
Same category as `scenario/service.py`'s own MVP threshold values (60/70/65) — a reasonable, explicit, documented default (see DECISIONS.md, Phase 9) rather than a value derived from real sales-conversation data, because none exists yet. Worth revisiting once Phase 15 (Stress Testing) or real usage shows whether a 10-point gap actually reads as "borderline" to a human reviewer.
Origin: Phase 9. Owner: Phase 15.

**P3 — Readiness verdict does not automatically recompute if evaluation scores ever change after the fact**
Deliberate (see DECISIONS.md, Phase 9) — a `readiness_results` row, once persisted, is treated as authoritative for that conversation rather than silently drifting. No mechanism exists yet (and none is needed yet, since Phase 8 evaluation is itself idempotent/immutable) for a future phase that might allow re-evaluation to also invalidate a stale readiness verdict.
Origin: Phase 9. Owner: revisit only if a future phase adds evaluation re-computation.

**P3 — Coaching session does not automatically regenerate if readiness/evaluation ever changes after the fact**
Same deliberate posture as the readiness item directly above, one layer up — see DECISIONS.md, Phase 10.
Origin: Phase 10. Owner: revisit only if a future phase adds evaluation/readiness re-computation.

**P3 — Coaching's priority pick carries no cross-competency causal reasoning (e.g., "weak closing traced back to weak discovery")**
MASTER_PROMPT.md's COMPETENCY/SKILL GRAPH section gestures at this kind of root-cause claim, but explicitly requires it never be made "without evidence" — and no such cross-competency evidence exists without `skill_graph_edges` (Phase 14, not yet built; ARCHITECTURE.md explicitly deferred "full skill graph with dependency modeling" past Milestone 1/2). Phase 10's priority pick and its stated reason are both single-competency facts (that competency's own gap or margin) — correct and evidence-backed, but narrower than what a full root-cause engine would eventually provide.
Origin: Phase 10. Owner: Phase 14.

**P3 — Drill does not automatically regenerate if coaching/readiness/evaluation ever changes after the fact**
Same deliberate posture as readiness's and coaching's identical decisions, one layer further — see DECISIONS.md, Phase 11. Purely a behavioral-consistency choice here (drill generation is free; there's no LLM cost to avoid), not a cost-avoidance one.
Origin: Phase 11. Owner: revisit only if a future phase adds re-computation anywhere upstream.

**P3 — `READY_COMFORTABLE_MARGIN` (10 points) is a placeholder judgment call, not calibrated against real transcripts**
Deliberately reuses `AT_RISK_MARGIN`'s exact value and reasoning as a separate, independently named constant (see DECISIONS.md, Phase 12) rather than an unrelated new guess — but is, like `AT_RISK_MARGIN` itself, not derived from real sales-conversation data, because none exists yet. Same owner and same open question as the `AT_RISK_MARGIN` item above: worth revisiting once Phase 15 (Stress Testing) or real usage shows whether either constant's value actually reads as intended to a human reviewer.
Origin: Phase 12. Owner: Phase 15.

**P3 — The difficulty recommendation is never persisted, so there is no historical record of what was recommended at a given point in time**
Deliberate — per this phase's own explicit instruction not to create a table absent a genuine persistence requirement, `difficulty/service.py` always recomputes fresh from already-durable upstream data rather than snapshotting a result. This means if evaluation or readiness data were ever corrected retroactively (neither currently possible — both are immutable once persisted, see the two P3 items above), a difficulty recommendation shown to a rep earlier could not be distinguished from one computed after such a correction. Not a real gap today, since nothing upstream can currently change after the fact either. See DECISIONS.md, Phase 12.
Origin: Phase 12. Owner: revisit only if a future phase both (a) allows evaluation/readiness re-computation and (b) needs recommendation history specifically.

## Resolved

**P2 — `Result` screen renders Phase 4 mock data instead of real evaluation + readiness data** *(resolved Phase 9)*
`frontend/src/api/readiness.ts` sequences Phase 8's evaluation trigger and Phase 9's combined result fetch; `App.tsx` and `Conversation.tsx` thread the real conversation id through instead of a raw transcript. `Result.tsx` itself needed no changes — the Phase 4 mock-data types already matched the real API shape once adapted from snake_case (see DECISIONS.md, Phase 9).


**P2 — Conversation end-condition thresholds undefined** *(resolved Phase 7)*
Turn-limit end condition uses `scenario.max_turns` (already in the data model). Patience-exhausted end condition uses the `BuyerState` schema's own clamp floor (`patience <= 0`). Explicit-close is a dedicated `POST /conversations/{id}/close` endpoint. See DECISIONS.md, Phase 7, for the reasoning behind each choice.

**P2 — Buyer module has no persistence or API route yet** *(resolved Phase 7)*
`app/conversation/service.py` now loads persisted `current_buyer_state` from the DB, calls the unchanged `buyer/service.run_buyer_turn()` once per turn, and persists the result (`Conversation.current_buyer_state`, a new `Message` pair, and a `BuyerStateHistory` row) inside a single DB transaction per turn. Wired to `POST /conversations/{id}/turns` in `app/api/routes/conversation.py`.

