# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 8 — Evaluation Engine
**Current Checkpoint:** Phase 8 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 5`; the P2 visual-verification item remains open in KNOWN_ISSUES.md for the record, not re-litigated); Phase 6 — Adaptive AI Buyer (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 6` after review); Phase 7 — Conversation Engine (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 7` after review)

**Current Objective:** Get sign-off that the Evaluation Engine correctly turns a completed conversation's transcript into evidence-grounded, per-competency scores — evidence extraction, deterministic verification (the anti-hallucination invariant), competency scoring, persistence, and a public evaluation API — all still fully testable without a real API key, before starting Phase 9 (Readiness Engine).

**Completed Work:**
- Phases 0–7 approved (see CHANGELOG.md for detail)
- Phase 8 Evaluation Engine built and verified by automated test + live manual smoke test:
  - Verified the Phase 7 baseline first (94/94 tests, clean frontend build, working tree clean) — surfaced and got your explicit sign-off on the Phase 7 checkpoint discrepancy before starting any Phase 8 work
  - Confirmed the DB schema (`evaluations`, `evidence`, `competencies`) already existed from Phase 2/3, purpose-built for this exact phase — **no new Alembic migration needed**; verified via `alembic upgrade head` against a fresh DB (all 11 tables present)
  - `app/evaluation/extraction.py` — evidence-candidate structured output (`EvidenceCandidate`/`EvidenceExtractionResult`); candidates reference `turn_index` (already visible in the transcript shown to the model), never a raw `message_id`, so the deterministic turn→message mapping happens in code, never in the model's own output
  - `app/evaluation/verification.py` — the deterministic anti-hallucination gate (pure function, no LLM, no DB): a candidate persists only if its turn exists, that message's `sender` is `"rep"` (never a buyer line, checked independently of the extraction prompt's own instruction), and the quote is an actual substring of what was really said
  - `app/evaluation/scoring.py` — per-competency scoring, LLM-assisted only when there's verified evidence to interpret; deterministic `no_evidence_result`/`unavailable_result` (zero LLM calls) otherwise, worded differently so a reviewer can tell "not demonstrated" apart from "couldn't be scored"; same defense-in-depth regex leak-scrubber pattern as `buyer/response.py`
  - `app/evaluation/service.py` — orchestrates extraction → verification → scoring → persistence as one DB transaction (rollback on unexpected failure); idempotent — a repeat `evaluate_conversation` call returns the existing rows rather than re-computing or hitting the `(conversation_id, competency_id)` unique constraint
  - `app/evaluation/schemas.py` — public API contract (`ConversationEvaluationOut`/`EvaluationOut`/`EvidenceOut`), structurally excludes hidden buyer state, system-prompt/provider detail, and internal reasoning
  - `app/api/routes/evaluation.py` — `POST /conversations/{id}/evaluate` (idempotent trigger, 404/409 on bad state), `GET /conversations/{id}/evaluation` (fetch, 404 if not yet evaluated); reuses the existing `get_llm_provider` dependency, so tests never need a real key
  - 26 new backend tests (120 total, all passing) — extraction/verification/scoring at both the unit level (pure `verify_evidence`, deterministic scoring fallbacks) and full API-integration level, including a direct end-to-end proof that a fabricated quote mixed into an otherwise-valid extraction response never reaches the public API
  - Live manual smoke test against a real running `uvicorn` server (not just `TestClient`): health check, conversation creation, immediate close (zero turns), evaluation trigger with no `LLM_API_KEY` set (correct deterministic "no evidence observed" result for all 3 competencies), evaluation retrieval, and 404 handling — all confirmed correct
  - Frontend: intentionally **not** touched this phase. Inspected `types.ts`/`screens/Result.tsx` per the "inspect existing frontend architecture" instruction — the Phase 4 `ReadinessResult` type bundles Phase 8 evaluation data together with the Phase 9 readiness verdict in one object/screen, so wiring `Result` now would mean fabricating a placeholder verdict, which is out of this phase's boundary. Recorded as a known limitation for Phase 9 to resolve in one coherent change, not decided unilaterally here. `npm run build` re-verified clean as a pure regression check (0 type errors, no files changed).

**In Progress:** Awaiting your review of Phase 8.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin Phase 9 — Readiness Engine (deterministic READY/NOT_READY/AT_RISK decision from Phase 8's competency scores + scenario-specific thresholds; also the natural point to finally wire the frontend `Result` screen to real data, since Phase 9 supplies the missing verdict half of that screen).

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- `Result` screen still renders Phase 4 mock data — not wired to real Phase 8 evaluation data this phase (see KNOWN_ISSUES.md and DECISIONS.md for the reasoning; owned by Phase 9).
- Phase 5 frontend integration still not visually verified end-to-end in this sandbox (unchanged, pre-existing).
- Phase 7 frontend conversation UI not visually verified end-to-end in this sandbox (unchanged, pre-existing) — same environment limitation (background dev processes reclaimed between tool calls).
- No scripted buyer opening line — unchanged, pre-existing (Phase 7 decision, still under your review).

**Known P3:**
- Rejected (hallucinated/ungrounded) evidence candidates are silently dropped, not logged anywhere — fine for MVP correctness, but Phase 15/18 will likely want a rejection log to measure real-model hallucination rates.
- `buyer_state_history` unbounded growth (Phase 20/21).
- Dev-mode auto schema creation needs an explicit production guard (Phase 21).
- MVP scenario seeding rides the same dev-only guard (Phase 21).
- `AnthropicProvider` still never exercised against the real Anthropic API for any module (buyer, or now evaluation) — needs one live smoke test once a real `LLM_API_KEY` is added.
- Turn-submission responses include the full message history on every turn — irrelevant at MVP scale (max 12 turns).
- MVP is single-user via a synthetic default user (`get_or_create_default_user`) — intentional, `user_id` FK already in place for when real auth arrives (Milestone 3).

**Technical Debt:** Same as before, plus the P3 items above.
**Last Successful Test:** `pytest -v` (backend) — 120 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors (regression check only, no frontend files changed this phase). `alembic upgrade head` — clean against a fresh DB, all 11 tables present. Live `uvicorn` smoke test — health, conversation creation/close, evaluation trigger with graceful degradation, evaluation retrieval, and 404 handling all confirmed correct via `curl`.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 8.
