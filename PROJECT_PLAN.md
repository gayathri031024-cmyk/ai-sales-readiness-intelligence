# PROJECT_PLAN.md

Full roadmap and status. See `PROJECT_STATE.md` for the live "what's next" snapshot — this file is the complete picture.

## Milestones

- **Milestone 1 — Technical Proof:** Scenario → AI Buyer → Conversation → Evidence → Evaluation → Readiness (Phases 0–9)
- **Milestone 2 — Product Proof:** + Root Cause → Coaching → Targeted Drill → Reassessment (Phases 10–12, 14)
- **Milestone 3 — Founder-Ready:** + RAG → Skill Intelligence → Manager View → Benchmarking → Security → Deployment → 2-minute demo (Phases 13, 15–26)

## Phase Status

| Phase | Name | Status | Checkpoint |
|---|---|---|---|
| 0 | Product Strategy | ✅ Done | PASSED |
| 1 | System Architecture | ✅ Done | PASSED |
| 2 | Data Model | ✅ Done | PASSED |
| 3 | Project Foundation | ✅ Done | PASSED |
| 4 | Core UX | ✅ Done | PASSED |
| 5 | Scenario Engine | ✅ Done | PASSED |
| 6 | Adaptive AI Buyer | ✅ Done | PASSED |
| 7 | Conversation Engine | ✅ Done | PASSED |
| 8 | Evaluation Engine | ✅ Done | PASSED |
| 9 | Readiness Engine | 🔄 In Progress | pending review |
| 10 | AI Coach | Not started | — |
| 11 | Targeted Drills | Not started | — |
| 12 | Adaptive Difficulty | Not started | — |
| 13 | Product RAG | Not started | — |
| 14 | Skill Graph | Not started | — |
| 15 | Stress Testing | Not started | — |
| 16 | Manager Intelligence | Not started | — |
| 17 | Voice | Not started | — |
| 18 | AI Evaluation Benchmark | Not started | — |
| 19 | Security | Not started | — |
| 20 | Cost Optimization | Not started | — |
| 21 | Deployment | Not started | — |
| 22 | Product Polish | Not started | — |
| 23 | Founder Demo | Not started | — |
| 24 | Documentation | Not started | — |
| 25 | CTO Review | Not started | — |
| 26 | Founder Outreach | Not started | — |

## Acceptance Criteria Per Completed/Active Phase

**Phase 0:** Target user, personas, JTBD, problem statement, MVP boundary via Scope Gate, differentiation, principles, metrics, demo strategy all defined; 7 output-rule questions answered.

**Phase 1:** Frontend/backend/module architecture, AI architecture (2-component split), data flow, state management, error handling, security boundaries defined; deterministic-readiness principle enforced at the module level.

**Phase 2:** MVP-scoped schema for every module; readiness thresholds normalized and queryable; evidence traceable to a real transcript line; no non-MVP tables introduced.

**Phase 3:** Repo scaffolded; backend boots and serves real HTTP traffic; `/health` confirms DB connectivity; migrations apply cleanly and produce the exact Phase 2 schema; tests pass; frontend builds, type-checks, and its dev server successfully proxies to the live backend; CI workflow runs backend tests on push. Repo committed in 10 small units, tagged `v0.3-foundation`, packaged as a portable zip including git history. **Verification is done. Awaiting checkpoint sign-off.**

**Phase 4:** All 3 MVP screens built as real components (not static mockups); deliberate visual direction grounded in the product's subject, not a generic AI-tool default; one consistent signature element (Evidence Chip) tying every score to a cited transcript line; typed contract so mock data is swappable for real data without a UI rewrite; verified with actual rendered screenshots, not just a successful build. **PASSED.**

**Phase 5:** The single MVP scenario (persona, product context, objection, difficulty, thresholds) is real, seeded, and idempotent — not hardcoded in frontend mock files; `GET /scenarios` and `GET /scenarios/{id}` exist with a schema layer independent of the ORM models; buyer hidden state (`base_state`) is confirmed, by test, to never appear in any scenario response; `StartScenario` renders real backend data via a typed adapter layer. **PASSED** — you explicitly confirmed `CHECKPOINT PASSED — Phase 5`. The visual end-to-end verification item remains open in `KNOWN_ISSUES.md` P2 for the record (not re-litigated by the override).

**Phase 6:** The Adaptive AI Buyer foundation is real and provider-agnostic. Hidden state (trust/patience/budget_sensitivity/interest) is a bounded, clamped, pure schema. Rep behavior is classified by an LLM into a fixed 10-label set via structured output (retry-once, degrade-to-UNCLEAR on failure). State transitions are a deterministic Python rule table — no LLM involved, every label covered. Buyer replies are generated with numeric state kept entirely out of the prompt (qualitative hints only), explicit anti-injection system-prompt rules, and an independent regex-based leak scrubber as defense-in-depth. The turn pipeline is a small 3-node LangGraph graph (classify → update state → reply) with internal graceful degradation at every node, so the graph itself never crashes on an LLM failure. All of this ships as `app/buyer/service.py::run_buyer_turn` — a pure function Phase 7 calls, with **no DB writes and no API route**, per this phase's explicit boundary. 60 new tests, 67 total, all passing with zero LLM API key / zero network calls. **PASSED** — you explicitly confirmed `CHECKPOINT PASSED — Phase 6`.

**Phase 7:** The single-turn buyer engine from Phase 6 is now a real, persistent, multi-turn conversation. `app/conversation/service.py` loads persisted hidden state, calls the unchanged `run_buyer_turn()` once per turn, and persists the result (updated state, both messages, a `buyer_state_history` row) inside one DB transaction — verified, not just structurally implied, that turn N+1 builds on turn N's persisted state rather than resetting. End conditions (turn limit, patience exhaustion, explicit close) use fields the data model already established, no new scoring system invented. Four routes (`POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/turns`, `POST /conversations/{id}/close`) return a public conversation shape that structurally excludes hidden state and internal classification detail. The frontend's Conversation screen now drives this real API instead of canned mock replies. 27 new tests, 94 total, all passing with zero LLM API key / zero network calls; also smoke-tested against a real running `uvicorn` server. **PASSED** — you explicitly confirmed `CHECKPOINT PASSED — Phase 7`.

**Phase 8:** The evidence-based evaluation engine. `evaluation/extraction.py` proposes candidate evidence via structured LLM output, referencing a `turn_index` rather than a fabricable `message_id`; `evaluation/verification.py` (pure, deterministic, no LLM) is what actually decides whether a candidate persists — grounded in a real message, attributed to the rep (never the buyer), and an actual substring of what was said. `evaluation/scoring.py` scores each of the 3 MVP competencies from verified evidence only, skipping the LLM entirely (deterministic result) when there's no evidence or when scoring genuinely fails, so cost and hallucination risk are minimized exactly where the project's COST section calls for. `evaluation/service.py` persists one `Evaluation` + its `Evidence` rows per competency per conversation, idempotently — a repeat evaluation call returns the existing result rather than re-computing. Two routes (`POST /conversations/{id}/evaluate`, `GET /conversations/{id}/evaluation`) expose only the public shape — no hidden buyer state, no system-prompt/provider detail, no internal reasoning. No migration was needed (Phase 2's schema already had `evaluations`/`evidence`/`competencies`). 26 new tests, 120 total, all passing with zero LLM API key / zero network calls; also smoke-tested against a real running `uvicorn` server. Frontend intentionally not touched this phase — see `KNOWN_ISSUES.md`. **PASSED** — you explicitly confirmed `CHECKPOINT PASSED — Phase 8`.

**Phase 9 (current):** The deterministic readiness decision engine. `readiness/decision.py` is pure Python — no LLM anywhere in this module or anything it calls (ARCHITECTURE.md §3's module boundary, test-enforced): READY if every competency clears its scenario-specific threshold; otherwise NOT_READY or AT_RISK depending on whether the worst gap among failing competencies is within a new named constant (`AT_RISK_MARGIN = 10` points) or beyond it, with reasoning text naming every failing competency by score and required minimum. `readiness/service.py` persists a `thresholds_snapshot` alongside the verdict (the actual scenario thresholds at computation time, per the existing Phase 2 data model), is idempotent (a persisted verdict is treated as authoritative rather than silently recomputed), and deliberately never triggers Phase 8's evaluation step itself, even lazily — preserving the "readiness never calls anything that could transitively call an LLM" guarantee for the whole call graph. Three routes (`POST`/`GET /conversations/{id}/readiness`, `GET /conversations/{id}/result`) expose only the public shape. No migration was needed (Phase 2's schema already had `readiness_results`). Notably, `app/readiness/decision.py`/`schemas.py`/`service.py` were found already present and uncommitted at the start of this phase, of unexplained origin — treated as an unverified discrepancy, independently checked against the schema and control docs, then proven correct through 24 real tests rather than trusted on inspection (see DECISIONS.md, Phase 9, for the full account). 144 total tests passing, zero LLM API key / zero network calls. Frontend wired to real data this phase — `Result.tsx`/`types.ts` needed no changes at all, since the Phase 4 mock-data types already matched the real API shape; only `App.tsx`/`Conversation.tsx` and a new `api/readiness.ts` adapter changed. Verified one layer deeper than any prior phase: the full request chain through the actual Vite dev-server proxy, not just direct backend calls — though a rendered-browser screenshot is still outstanding (see `KNOWN_ISSUES.md`). **Not yet checkpoint-approved — awaiting your review.**
