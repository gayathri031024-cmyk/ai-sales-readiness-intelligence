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

### Decision: Build the UX shell with typed mock data before any backend logic exists (Phase 4 precedes Phases 5–9)
**Why:** Matches the phase roadmap's own ordering — validates the interaction design (3-screen journey, evidence-first result screen) independent of AI reliability work, and catches UX problems before they're expensive to fix in a wired-up system.
**Alternatives considered:** Build screens phase-by-phase alongside each backend module (UI for scenarios in Phase 5, UI for conversation in Phase 7, etc.)
**Tradeoff:** Mock data must later be swapped for real API calls — mitigated by writing `types.ts` first as the contract both mock data and future real responses conform to, so the swap is a data-source change, not a UI rewrite. All mock files are explicitly marked `MOCK` in a header comment per the code quality rule.
**Phase:** 4

### Decision: No routing library for the 3-screen MVP flow
**Why:** Start → Conversation → Result is strictly linear with no need for deep-linking or back/forward at this stage. A local `useState` screen switcher in `App.tsx` is simpler and has zero new dependencies.
**Alternatives considered:** react-router-dom.
**Tradeoff:** No shareable URLs per screen yet; acceptable for an MVP demo flow, revisit if Phase 16 (Manager Intelligence) or multi-scenario browsing needs real routes.
**Phase:** 4

### Decision: Evidence Chip as the product's signature UI element
**Why:** The core differentiation (per Phase 0) is "every score has evidence" — the design should make that promise visually unmistakable and consistent everywhere a score appears, not just state it in prose.
**Alternatives considered:** A generic score gauge/progress-bar as the signature element (rejected — flagged in the frontend-design skill as a template default: "big number + small label + gradient accent").
**Tradeoff:** None significant — the element is cheap to implement and reused as-is across every competency card.
**Phase:** 4

### Decision: "Briefing room / instrument panel" visual direction (dark, amber accent, Space Grotesk + Inter + JetBrains Mono)
**Why:** Grounded in the actual subject — a tool for preparing for a high-stakes call, not a playful LMS. Deliberately avoided the three AI-tool-default looks named in the frontend-design skill (cream+terracotta serif, black+neon, broadsheet hairlines).
**Alternatives considered:** Light theme with a single bright accent (rejected as closer to a generic SaaS dashboard default, less differentiated for this subject).
**Tradeoff:** None significant at this stage; revisit only if user testing in a later phase suggests the tone reads as too severe for new reps.
**Phase:** 4
