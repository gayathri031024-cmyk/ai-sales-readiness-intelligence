# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 14 — Skill Graph (competency dependency graph + root-cause analysis)
**Current Checkpoint:** Phase 14 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED); Phase 6 — Adaptive AI Buyer (PASSED); Phase 7 — Conversation Engine (PASSED); Phase 8 — Evaluation Engine (PASSED); Phase 9 — Readiness Engine (PASSED); Phase 10 — AI Coach (PASSED); Phase 11 — Targeted Drills (PASSED); Phase 12 — Adaptive Difficulty (PASSED); Phase 13 — Product RAG (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 13`)

**Current Objective:** Get sign-off that the competency dependency graph correctly, deterministically, and honestly surfaces within-conversation correlated weaknesses — never claiming causation, never fabricating a competency the MVP doesn't actually score, never leaking hidden state.

**Scope note (important):** A later prompt in this same working session described a materially different "Phase 14" — a longitudinal, cross-conversation Sales DNA profile (historical trend, confidence-from-evidence-volume, persisted behavioral patterns, a `/salespeople/{user_id}/skill-profile` endpoint). This was surfaced as an explicit conflict rather than silently resolved either way. You decided: keep the already-built, already-tested competency dependency graph / root-cause work as Phase 14; treat the longitudinal profile as new, separately-scoped future work ("Phase 14b" in `PROJECT_PLAN.md`, not yet started). See DECISIONS.md, Phase 14, for the full reasoning.

**Completed Work:**
- Phases 0–13 approved (see CHANGELOG.md for detail)
- Phase 14 competency dependency graph + root-cause analysis built and verified by automated test + live manual smoke test:
  - Verified the Phase 13 baseline first: HEAD `6edcb70`, Phase 13 feature/test/docs commits (`5b7badf`/`1002699`/`6edcb70`) confirmed present, 241/241 tests fresh, working tree clean.
  - Derived scope from MASTER_PROMPT.md's COMPETENCY / SKILL GRAPH section and `DATA_MODEL.md` §3 ("Explicitly Deferred" — `skill_graph_edges` was named but never schema'd) before writing any code.
  - `SkillGraphEdge` ORM model — a small, static, hand-authored "depends_on" reference table (Closing→Discovery, Closing→Objection Handling, Objection Handling→Discovery), same posture as `Competency`/`ScenarioCompetencyThreshold`. Alembic migration `0e7ff0f54546` (down-revision `ed1e90345d8b`, Phase 13's). Corrected the stale `models.py` docstring again.
  - `app/skill_graph/seed.py::seed_mvp_skill_graph` — idempotent seed, same pattern as `seed_mvp_scenario`, wired into `main.py`'s dev-only lifespan guard (runs after scenario seeding, since it references already-seeded `Competency` rows).
  - `app/skill_graph/analysis.py::find_related_weaknesses` — pure, deterministic, zero-LLM (no provider parameter at all, test-enforced). For each competency that failed its threshold, checks its "depends_on" edges; if an upstream competency also failed in that same conversation, surfaces it as a possible contributing factor in deliberately hedged language ("may be a contributing factor"), quoting the upstream competency's own already-verified diagnosis as evidence. Never claims causation — MASTER_PROMPT's explicit instruction.
  - `app/skill_graph/service.py::compute_root_cause_analysis` — orchestration, requires evaluation to exist (409 if not), deliberately does NOT require the readiness verdict (this module never reads it). Persists nothing — pure, free-to-recompute, same reasoning as Phase 12.
  - One route: `GET /conversations/{id}/root-cause-analysis`, wired into `main.py`.
  - Scoped only to the 3 MVP-seeded competencies (discovery, objection_handling, closing) — the other 4 MASTER_PROMPT names have no backing data anywhere in the MVP. See DECISIONS.md.
  - 18 new backend tests in `test_skill_graph.py` (259 total, all passing) — pure unit tests for `find_related_weaknesses` (empty cases, single-level, multi-level chains, missing-diagnosis exclusion, unknown-competency safety, hedged-not-causal wording), seed idempotency + real-competency-reference checks, and full API-level tests (409/404, correct single- and multi-level surfacing, correct omission when no failing upstream exists, zero-LLM-call guarantee, deterministic repeatability, no hidden-state leakage).
  - Live manual verification against a real running `uvicorn` server: 409 before evaluation, 404 for an unknown conversation, route present in the live OpenAPI schema, `/scenarios` re-checked for hidden buyer-state leakage as a regression check (still absent).
  - `alembic upgrade head` verified clean against a fresh DB — all 5 migrations apply in order, 16 schema tables (17 including `alembic_version`).
  - Checked for and confirmed no accidental artifacts are tracked via `git status --ignored`; no `.env`, real secrets, `dev.db`, `node_modules`, `dist`, `__pycache__`, or `.pytest_cache` tracked.
  - No per-user authorization added or needed beyond what already exists — the MVP has no real multi-user auth yet (unchanged since Phase 7); this endpoint is scoped by conversation id like every other conversation-scoped endpoint.
  - Frontend not touched — same reasoning as Phases 10–13.

**In Progress:** Awaiting your review of Phase 14.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin the next phase (either Phase 14b, the longitudinal Sales DNA profile, or Phase 15, Stress Testing — your call at that point).

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- Phase 14's "Skill Graph" is a within-conversation dependency graph, not the longitudinal cross-conversation Sales DNA profile the product vision describes. Explicitly deferred as Phase 14b, not yet started.
- Root-cause analysis only covers the 3 MVP-seeded competencies — the full 7-competency graph MASTER_PROMPT.md names is not built (the other 4 have no backing data).
- `HashingEmbeddingProvider` (Phase 13's default, and the only embedding provider exercised by any test) is lexical, not semantic. Owner: switch production to `EMBEDDING_PROVIDER=sentence_transformer` once network access allows exercising it.
- The knowledge base has no per-org/tenant scoping (unchanged from Phase 13). Owner: Phase 19 (Security).
- Product RAG, adaptive difficulty, drills, and coaching all have no frontend yet — API-only (unchanged).
- The recommendation is advisory only against the MVP's single seeded scenario (unchanged from Phase 12).
- The training loop's reassessment step is still not implemented (unchanged from Phase 11).
- Phase 9 frontend Result integration not visually screenshot-verified in an actual browser (unchanged).
- Phase 5 and Phase 7 frontend integration still carry the same pre-existing, unresolved visual-verification gap (unchanged).
- No scripted buyer opening line (unchanged, Phase 7 decision, still under your review).

**Known P3:**
- The 3-edge skill graph is a documented judgment call, not calibrated against real transcript data. Owner: revisit once real transcript data exists.
- Root-cause correlation is a single-conversation signal only — cannot distinguish a one-off bad day from a recurring pattern. Owner: Phase 14b.
- `SentenceTransformerEmbeddingProvider` has never been exercised or tested in this environment (unchanged from Phase 13). Owner: final integration.
- Retrieval is pure-Python in-process cosine similarity, O(n) per query (unchanged from Phase 13). Owner: Phase 21.
- Grounding verification only confirms a cited chunk id was retrieved, not that the prose faithfully represents it (unchanged from Phase 13). Owner: Phase 18.
- `READY_COMFORTABLE_MARGIN = 10` is a placeholder judgment call (unchanged from Phase 12). Owner: Phase 15.
- The difficulty recommendation does not persist (unchanged, deliberate).
- Drill does not auto-regenerate if coaching/readiness/evaluation ever changes after the fact (unchanged, deliberate).
- Coaching's priority pick carries no cross-competency causal reasoning (partially addressed by Phase 14's within-conversation correlation; full historical reasoning still owned by Phase 14b).
- Coaching session does not auto-regenerate if readiness/evaluation ever changes (unchanged, deliberate).
- Readiness verdict does not auto-recompute if evaluation scores ever change (unchanged, deliberate).
- Rejected (hallucinated/ungrounded) evidence candidates are silently dropped, not logged anywhere (unchanged). Owner: Phase 15/18.
- `buyer_state_history` unbounded growth (unchanged). Owner: Phase 20/21.
- Dev-mode auto schema creation needs an explicit production guard (unchanged). Owner: Phase 21.
- MVP scenario seeding rides the same dev-only guard (unchanged). Owner: Phase 21.
- `AnthropicProvider` still never exercised against the real Anthropic API for any module (unchanged). Owner: final integration.
- Turn-submission responses include full message history on every turn (unchanged, irrelevant at MVP scale).
- MVP is single-user via a synthetic default user (unchanged, intentional — `user_id` FK already in place for Milestone 3).

**Technical Debt:** Same as before, plus the P2/P3 items above.
**Last Successful Test:** `pytest -v` (backend) — 259 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors, unaffected. `alembic upgrade head` — clean against a fresh DB, all five migrations apply in order, 16 schema tables present (17 including `alembic_version`). Live `uvicorn` smoke test confirmed correct request/response behavior end to end, including the 409/404 preconditions and the hidden-state regression check.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 14.
