# DECISIONS.md

Record of significant architecture/product decisions. Append-only — do not silently overwrite past entries.

---

### Decision: Modular monolith, not microservices
**Why:** MVP scope is one team, one deployable unit, no independent scaling needs yet.
**Alternatives considered:** Microservices per module (scenario/buyer/evaluation/readiness).
**Tradeoff:** Slightly less "impressive-looking" architecture; far less operational complexity and faster iteration. Revisit only if a concrete scaling or team-ownership reason emerges.
**Phase:** 1

---

### Decision: Readiness engine is deterministic Python, never an LLM call
**Why:** Core product principle from Phase 0 — the LLM proposes evidence/diagnosis, a rules engine decides READY/NOT READY/AT RISK. This must be enforceable, not just prompted.
**Alternatives considered:** Let the LLM output a readiness verdict directly as part of evaluation.
**Tradeoff:** Slightly less flexible (thresholds must be defined explicitly per scenario) in exchange for consistency, testability, and a legible answer to "why was this rep marked not ready" that doesn't depend on model variance.
**Phase:** 1

---

### Decision: Two separate AI components — LangGraph for conversation, plain sequential pipeline for evaluation
**Why:** The conversation is genuinely stateful and needs looping (LangGraph fits). Evaluation is a linear post-hoc pipeline with no branching/looping requirement — a LangGraph graph there would add framework overhead without benefit.
**Alternatives considered:** One LangGraph graph covering both conversation and evaluation.
**Tradeoff:** Two code paths to maintain instead of one, but each is simpler and easier to test in isolation.
**Phase:** 1

---

### Decision: Buyer state updates are deterministic given LLM-classified rep behavior, not raw LLM-generated numbers
**Why:** Directly addresses the Phase 0 risk assumption that the LLM might leak or inconsistently manage hidden buyer state. The LLM's job narrows to classification (what did the rep just do); a Python rule table converts that into state deltas.
**Alternatives considered:** Let the LLM directly output updated state values each turn.
**Tradeoff:** Less "emergent" buyer behavior, more predictable and testable — appropriate for an MVP that needs to prove reliability first.
**Phase:** 1

---

### Decision: Buyer hidden state excluded from API response schemas at the serializer level
**Why:** "Never send hidden state to the frontend" needs to be an architectural guarantee, not a rule someone might forget in a handler.
**Alternatives considered:** Rely on backend code discipline to simply not include those fields.
**Tradeoff:** Slightly more schema definition work upfront; removes an entire class of accidental-leak bugs.
**Phase:** 1

---

### Decision: No RAG / pgvector in the MVP
**Why:** Per Phase 0 Scope Gate — RAG is a Milestone 3 feature. The MVP's single hardcoded scenario doesn't need document grounding yet.
**Alternatives considered:** Include pgvector from the start "since we'll need it eventually."
**Tradeoff:** Will need a follow-up migration/phase when RAG is built (Phase 13); avoids unused infrastructure and schema complexity now.
**Phase:** 1

---

### Decision: One `evaluations` row per competency per conversation, not one bundled row
**Why:** Keeps evidence cleanly scoped to a single competency and matches "every score has evidence" as a per-competency guarantee rather than one evidence blob covering everything.
**Alternatives considered:** Single `evaluations` row per conversation with a jsonb map of competency → score/evidence.
**Tradeoff:** More rows, but trivial to query/index and much easier to unit-test the readiness engine against.
**Phase:** 2

---

### Decision: Evidence is a foreign key to a specific `messages` row, not free text
**Why:** Directly enforces the "no hallucinated quotes" assumption from Phase 0 — if evidence must reference a real message id, the evaluator can't cite a line that was never said.
**Alternatives considered:** Store the quoted text directly on the evidence row with no link back to the transcript.
**Tradeoff:** Slightly more join complexity when displaying evidence; in exchange, evidence is provably traceable, which is exactly the kind of check Phase 15 (Stress Testing) and Phase 18 (AI Evaluation) will want to run automatically.
**Phase:** 2

---

### Decision: `buyer_state_history` exists as an append-only debug/audit log, not a product feature
**Why:** Needed to actually test (not just assume) whether hidden buyer state stays hidden and evolves sensibly — this is one of the explicit assumptions flagged in Phase 0.
**Alternatives considered:** Only store `current_buyer_state` on the conversation row, with no history.
**Tradeoff:** Unbounded row growth per conversation (flagged as a known P3 in the Phase 2 checkpoint); acceptable at prototype scale, worth a retention policy before real deployment.
**Phase:** 2

---

### Decision: Competency thresholds normalized into `scenario_competency_thresholds`, not a jsonb column
**Why:** The readiness engine (deterministic, per Phase 1) reads these directly — a real table is trivial to unit test and query, a jsonb blob is not.
**Alternatives considered:** Store thresholds as jsonb on the `scenarios` row.
**Tradeoff:** One more table, but the readiness engine's core logic becomes a straightforward SQL query + comparison instead of jsonb parsing.
**Phase:** 2
