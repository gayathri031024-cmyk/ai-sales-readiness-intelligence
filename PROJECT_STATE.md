# PROJECT_STATE.md

**Project:** AI Sales Readiness Intelligence

**Current Phase:** 13 — Product RAG
**Current Checkpoint:** Phase 13 — awaiting CHECKPOINT PASSED

**Completed Phases:** Phase 0 — Product Strategy (PASSED); Phase 1 — System Architecture (PASSED); Phase 2 — Data Model (PASSED); Phase 3 — Project Foundation (PASSED); Phase 4 — Core UX (PASSED); Phase 5 — Scenario Engine (PASSED); Phase 6 — Adaptive AI Buyer (PASSED); Phase 7 — Conversation Engine (PASSED); Phase 8 — Evaluation Engine (PASSED); Phase 9 — Readiness Engine (PASSED); Phase 10 — AI Coach (PASSED); Phase 11 — Targeted Drills (PASSED); Phase 12 — Adaptive Difficulty (PASSED — you explicitly confirmed `CHECKPOINT PASSED — Phase 12`)

**Current Objective:** Get sign-off that Product RAG correctly grounds product/company answers in uploaded knowledge documents — never inventing facts, correctly rejecting fabricated citations, structurally resistant to prompt injection embedded in documents, and honestly degrading (not guessing) when nothing in the knowledge base supports an answer or the LLM is unavailable.

**Completed Work:**
- Phases 0–12 approved (see CHANGELOG.md for detail)
- Phase 13 Product RAG built and verified by automated test + live manual smoke test:
  - Verified the Phase 12 baseline first: HEAD `19b0ee1`, Phase 12 feature commit `36062b6` and test commit `9fd8c04` both confirmed present with correct content, working tree clean, 214/214 tests passing fresh (LLM env vars unset, backend venv rebuilt from `requirements.txt`), `npm run build` clean, `alembic upgrade head` clean against a fresh DB (13 tables). No unexplained pre-existing Phase 13 work was found at the start of this phase.
  - Derived scope from MASTER_PROMPT.md's "RAG / PRODUCT KNOWLEDGE" section, `DATA_MODEL.md` §3 ("Explicitly Deferred"), and `ARCHITECTURE.md` §10 before writing any code. No control document specified chunking strategy, embedding provider, or a dev-environment vector store — these were resolved as explicit, recorded decisions (pure-Python cosine similarity now / pgvector at Phase 21; local deterministic `HashingEmbeddingProvider` default / no external embedding API) rather than guessed. See DECISIONS.md, Phase 13.
  - `app/ai/embedding_provider.py` / `embedding_factory.py` — new `EmbeddingProvider` abstraction mirroring `LLMProvider`'s swappable-transport split. `HashingEmbeddingProvider` is a **deterministic, zero-dependency, zero-network, lexical (not semantic)** bag-of-words feature-hashing vectorizer — the default, and the only provider exercised by any automated test. `SentenceTransformerEmbeddingProvider` (a real local open-source model) is implemented but **not exercised or tested in this environment** — same posture `AnthropicProvider` has held since Phase 6.
  - `app/knowledge/chunking.py` — pure, deterministic, boundary-aware character chunking, no LLM.
  - `app/knowledge/retrieval.py` — pure-Python cosine-similarity top-k over persisted chunk embeddings, no vector DB, independently unit-tested with no DB session at all.
  - `app/knowledge/generation.py` — the one LLM-touching stage. The model proposes an answer + cited chunk ids from a CONTEXT block built only from retrieved chunks; `verify_grounded_answer` (pure, deterministic, no LLM) never trusts that claim — it checks every cited id against the chunks actually retrieved and forces a fixed not-found answer if none survive. Anti-injection is structural: retrieved chunk text only ever reaches the user-turn CONTEXT block, never the fixed `SYSTEM_PROMPT` constant.
  - `app/knowledge/service.py` — ingest (chunk → embed → persist) and query (embed → retrieve → generate → verify) orchestration.
  - `KnowledgeDocument` / `KnowledgeChunk` ORM models added to `app/db/models.py` (`embedding` stored as a plain JSON float array, not pgvector); corrected a stale docstring that still listed `coaching_sessions`/`drills`/`knowledge_documents` as "deliberately absent" after the first two had already shipped in Phases 10-11.
  - Alembic migration `ed1e90345d8b` adds `knowledge_documents` and `knowledge_chunks` tables.
  - Four routes in `app/api/routes/knowledge.py`, wired into `main.py`: `POST`/`GET /knowledge/documents`, `GET /knowledge/documents/{id}`, `POST /knowledge/query`.
  - No per-org/tenant scoping — a single global corpus, correct for the still-single-tenant MVP (see DECISIONS.md, Phase 13).
  - 27 new backend tests in `test_knowledge.py` (241 total, all passing) — deterministic chunking and retrieval at the unit level, the citation-verification backstop at the unit level (accepts real citations, rejects fabricated ones, respects the model's own not-grounded claim, keeps only real ids from a mixed list), full API-level ingest to query pipeline, a zero-LLM-call guarantee when nothing is retrieved, graceful degradation when the LLM is unavailable, a structural prompt-injection test, and a conflicting-documents test confirming both sources' citations survive together.
  - Live manual verification against a real running `uvicorn` server, no `LLM_API_KEY` set: ingest a document containing an embedded prompt-injection attempt -> list -> query -> correctly degrades to a "temporarily unavailable" not-grounded response -> a second query with no matching content at all correctly returns the distinct not-found answer, with zero LLM involvement either way -> 404 for an unknown document -> all three route groups confirmed present in the live OpenAPI schema -> existing `/scenarios` endpoint re-checked for hidden buyer-state leakage as a regression check (still absent).
  - Checked for and confirmed no accidental artifacts are tracked via `git status --ignored`; no `.env`, no real secrets, no `dev.db`, no `node_modules`, no `dist`, no `__pycache__`, no `.pytest_cache` tracked.
  - Frontend not touched — no existing UI slot for document upload or a knowledge-query interface and no control document specifying one, same reasoning as Phase 10/11/12's identical frontend decisions. `npm run build` re-verified clean as a regression check only.

**In Progress:** Awaiting your review of Phase 13.

**Next Action:** Review this checkpoint report. If acceptable, say `CHECKPOINT PASSED` to begin the next phase.

**Known P0:** None.
**Known P1:** None.
**Known P2:**
- `HashingEmbeddingProvider` (the default, and the only embedding provider exercised by any test) is lexical, not semantic — no synonym/stemming awareness. Deliberate MVP default; real usage would likely see meaningfully worse retrieval recall than a real embedding model. Owner: switch production to `EMBEDDING_PROVIDER=sentence_transformer` once network access allows exercising it.
- The knowledge base has no per-org/tenant scoping — a single global corpus. Correct for the still-single-tenant MVP; would leak across tenants under real multi-tenant usage. Owner: Phase 19 (Security).
- Product RAG has no frontend at all yet — API-only, same reasoning as coaching/drills/difficulty.
- Adaptive difficulty has no frontend at all yet — API-only (unchanged from Phase 12).
- The recommendation is advisory only against the MVP's single seeded scenario (unchanged from Phase 12).
- The training loop's reassessment step is still not implemented (unchanged from Phase 11).
- Drills have no frontend at all yet — API-only (unchanged from Phase 11).
- Coaching has no frontend at all yet — API-only (unchanged from Phase 10).
- Phase 9 frontend Result integration not visually screenshot-verified in an actual browser (unchanged).
- Phase 5 and Phase 7 frontend integration still carry the same pre-existing, unresolved visual-verification gap (unchanged).
- No scripted buyer opening line (unchanged, Phase 7 decision, still under your review).

**Known P3:**
- `SentenceTransformerEmbeddingProvider` has never been exercised or tested in this environment (no network access to download model weights here) — same posture `AnthropicProvider` has held since Phase 6. Owner: final integration.
- Retrieval is pure-Python in-process cosine similarity, O(n) per query — fine at MVP scale, not built to scale to a large corpus. pgvector deferred to Phase 21.
- Grounding verification only confirms a cited chunk id was actually retrieved — it cannot confirm the model's prose faithfully represents that chunk's content. Owner: Phase 18 (AI Evaluation Benchmark).
- `READY_COMFORTABLE_MARGIN = 10` is a placeholder judgment call reusing `AT_RISK_MARGIN`'s value, not independently calibrated against real transcripts — owner Phase 15.
- The difficulty recommendation does not persist — deliberate (see DECISIONS.md, Phase 12).
- Drill does not auto-regenerate if coaching/readiness/evaluation ever changes after the fact — deliberate.
- Coaching's priority pick carries no cross-competency causal reasoning — owner Phase 14.
- Coaching session does not auto-regenerate if readiness/evaluation ever changes — deliberate.
- Readiness verdict does not auto-recompute if evaluation scores ever change — deliberate.
- Rejected (hallucinated/ungrounded) evidence candidates are silently dropped, not logged anywhere — owner Phase 15/18.
- `buyer_state_history` unbounded growth — owner Phase 20/21.
- Dev-mode auto schema creation needs an explicit production guard — owner Phase 21.
- MVP scenario seeding rides the same dev-only guard — owner Phase 21.
- `AnthropicProvider` still never exercised against the real Anthropic API for any module — owner final integration.
- Turn-submission responses include full message history on every turn — irrelevant at MVP scale.
- MVP is single-user via a synthetic default user — intentional, `user_id` FK already in place for Milestone 3.

**Technical Debt:** Same as before, plus the P2/P3 items above.
**Last Successful Test:** `pytest -v` (backend) — 241 passed, run fresh with `dev.db` removed and all LLM-related env vars unset. `npm run build` (frontend) — clean, 0 type errors, unaffected (no frontend files changed this phase). `alembic upgrade head` — clean against a fresh DB, all four migrations apply in order, 15 schema tables present (16 including `alembic_version`). Live `uvicorn` smoke test confirmed correct request/response behavior end to end, including both degradation paths (LLM unavailable vs. no matching content) and the anti-injection/citation-verification guarantees.
**Current Blockers:** Waiting on your review + `CHECKPOINT PASSED` for Phase 13.
