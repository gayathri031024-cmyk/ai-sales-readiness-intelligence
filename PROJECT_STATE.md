# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 6 — Adaptive AI Buyer
**Current Checkpoint:** Phase 6 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 5`; the P2 visual-verification item remains open in KNOWN_ISSUES.md for the record, not re-litigated)

**Current Objective:** Get sign-off that the Adaptive AI Buyer foundation is right — hidden state schema, deterministic state transitions, LLM classification with structured output, the LangGraph turn pipeline, prompt-injection defense, and graceful degradation — all provider-agnostic and fully testable without a real API key, before starting Phase 7 (Conversation Engine), which wires this into persistence and turn-taking.

**Completed Work:**
- Phases 0–5 approved (see CHANGELOG.md for detail)
- Phase 6 Adaptive AI Buyer built and verified by automated test:
  - `app/ai/provider.py` — `LLMProvider` protocol, `AnthropicProvider` (production, lazy client construction, never requires a key until called), `MockLLMProvider` (deterministic test double, zero cost/network)
  - `app/ai/structured.py` — structured-output helper: JSON parse + Pydantic validation, retry-once with the validation error fed back to the model, `StructuredOutputError` on a second failure
  - `app/ai/factory.py` — builds a real provider from `Settings` (`LLM_API_KEY` / `LLM_MODEL`, already established Phase 3) — used by future runtime code, never by tests
  - `app/buyer/state.py` — `BuyerState`: exactly trust/patience/budget_sensitivity/interest, bounded [0,100], clamped on construction, pure `apply_deltas()`
  - `app/buyer/classification.py` + `classify.py` — 10-label `RepBehavior` enum (incl. `prompt_injection_attempt`), delimited rep-message injection, degrades to `UNCLEAR` on any failure
  - `app/buyer/rules.py` — deterministic rule table, one fixed delta per label, no LLM dependency, every label covered
  - `app/buyer/persona.py` + `response.py` — prompt construction (numeric state never reaches the prompt, only qualitative hints), explicit anti-injection system-prompt rules, independent regex-based leak scrubber as defense-in-depth, graceful fallback replies
  - `app/buyer/graph.py` — LangGraph 3-node pipeline (classify → update state → generate reply), compiled once, cached
  - `app/buyer/service.py::run_buyer_turn` — the public entrypoint; does not touch the DB or FastAPI (that's Phase 7), per this phase's explicit PHASE BOUNDARY instruction
  - 60 new backend tests (67 total, all passing) — verified with `LLM_API_KEY`/`LLM_MODEL`/`ANTHROPIC_API_KEY` all unset, zero network calls
  - Phase 5 regression re-verified clean: original 7 backend tests still pass, `npm run build` still 0 type errors

**In Progress:** Awaiting your review of Phase 6.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin Phase 7 — Conversation Engine (turn persistence, turn-taking loop, end-condition logic, wiring `run_buyer_turn` into a real API route and the DB).

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- Conversation end-condition thresholds (turn limit / patience threshold / explicit close) still not concretely specified — Phase 6 built only the single-turn buyer graph, looping/end-conditions remain Phase 7's job.
- Buyer module has no persistence or API route yet — intentional per Phase 6's PHASE BOUNDARY; owned by Phase 7.
- Phase 5 frontend integration still not visually verified end-to-end in this sandbox — unchanged from before, still open, not part of Phase 6's scope.

**Known P3:**
- `buyer_state_history` unbounded growth (Phase 20/21).
- Dev-mode auto schema creation needs an explicit production guard (Phase 21).
- MVP scenario seeding rides the same dev-only guard, same owner (Phase 21).
- Mock data in `src/mock/` (buyer.ts, readiness.ts) still in use for Conversation/Result screens — untouched by Phase 6 (no frontend work in scope); will be replaced when Phase 7's API exists for the frontend to call.
- `AnthropicProvider` implemented but never exercised against the real API (no key provided, by design) — needs one live smoke test at final integration.

**Technical Debt:** Same as before, plus: `AnthropicProvider` live-path unverified (see P3 above).
**Last Successful Test:** `pytest -v` (backend) — 67 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 6.
