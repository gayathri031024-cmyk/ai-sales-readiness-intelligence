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

### Decision: MVP scenario data seeded via a dev-lifespan Python function, not a proper data migration
**Why:** There is exactly one hardcoded scenario for the entire MVP (per the Phase 0 Scope Gate — no scenario-authoring API exists or is planned before Milestone 3). A full Alembic data migration for a single row that only ever needs to exist in dev/demo is more infrastructure than the problem justifies right now.
**Alternatives considered:** An Alembic data migration alongside the schema migration; a `seed.py` CLI script run manually.
**Tradeoff:** This is explicitly *not* how production seeding should work once real scenario authoring exists — tracked as a known issue owned by Phase 21, same bucket as the existing dev-mode `Base.metadata.create_all` guard it rides alongside. `seed_mvp_scenario()` is idempotent and isolated in `scenario/service.py`, so replacing the mechanism later doesn't require touching its logic — a real Phase 21 migration can call the same function.
**Phase:** 5

### Decision: Scenario-specific competency thresholds (60 / 70 / 65) set deliberately uneven, with Objection Handling highest
**Why:** This scenario's whole premise (per Phase 0) is a price objection. A threshold set where every competency requires the same bar wouldn't test anything about the readiness engine's ability to fail a rep on the *specific* skill the scenario is designed to probe. Objection Handling at 70 (vs. 60/65 for the others) means a mediocre-but-not-terrible transcript should plausibly land on NOT_READY or AT_RISK because of the named challenge, not an arbitrary uniform cutoff.
**Alternatives considered:** Uniform threshold (e.g. 70 across all three) — rejected as less demonstrative of "scenario-specific readiness," which Phase 0/9 call out as a core differentiator over a single global score.
**Tradeoff:** These are placeholder judgment calls, not calibrated against real transcripts yet — Phase 15 (Stress Testing) is the actual point where these get validated against a range of good/bad conversations and adjusted if they produce a nonsensical READY/NOT_READY/AT_RISK spread.
**Phase:** 5

### Decision: `ScenarioDetailOut` includes `thresholds`, even though the frontend's `Scenario` type doesn't consume that field yet
**Why:** The readiness engine (Phase 9) and the Result screen need exactly this query (scenario → thresholds → competency). Since `get_scenario` already joins it, exposing it now avoids a second endpoint later. TypeScript's structural typing means the frontend safely ignores the extra field until Phase 9 adds it to `types.ts`.
**Alternatives considered:** A separate `GET /scenarios/{id}/thresholds` endpoint added in Phase 9 instead.
**Tradeoff:** Minor: the API response is very slightly larger than the current frontend needs. Judged acceptable — this is returning already-fetched data, not adding a new query or new coupling.
**Phase:** 5

### Decision: Numeric buyer state never enters the reply-generation prompt at all
**Why:** "Never reveal numeric hidden state" is far more reliable as a structural guarantee than a prompt instruction alone. `persona.py` translates each state dimension into a qualitative hint (e.g. trust 20 -> "You are wary and skeptical...") before building the system prompt — the actual integers 0-100 are simply absent from anything the model receives for reply generation. An explicit instruction not to reveal numbers is also present (defense in depth), but the primary control is that there is nothing numeric to leak in the first place.
**Alternatives considered:** Pass the raw numeric state and rely entirely on system-prompt instructions ("never reveal these numbers") to withhold it.
**Tradeoff:** Slightly less nuanced buyer behavior (three qualitative buckets per dimension instead of a continuous scale informing tone) in exchange for a leak surface that doesn't depend on the model faithfully following an instruction under adversarial pressure.
**Phase:** 6

### Decision: Independent regex-based leak scrubber as defense-in-depth, separate from the prompt-level controls
**Why:** `MASTER_PROMPT.md`'s AI RELIABILITY section explicitly calls out hallucination as a risk to account for, not just prompt-injection. Even with numeric state kept out of the prompt (see above), a future real model could still hallucinate a specific number, self-disclose as an AI, or reference "my system prompt" unprompted. `response.py::_looks_like_leak` is a second, independent layer that pattern-matches on that class of output and substitutes a safe in-character fallback line rather than shipping it. Deliberately narrow patterns (e.g. `trust score: 45`, not just the word "trust") to avoid false-positiving on ordinary buyer dialogue that happens to use words like "trust" or "patience" in a normal business sense — covered by a dedicated test.
**Alternatives considered:** Rely solely on the system prompt's instructions; add a second LLM call to judge whether a reply leaked anything (rejected as unnecessary cost/latency for what a cheap regex layer already catches for the known leak shapes).
**Tradeoff:** A regex layer can't catch every conceivable phrasing of a leak, and could in principle scrub a legitimate reply that happens to match a pattern — mitigated by keeping patterns narrow and testing the false-positive case explicitly. This is explicitly a second layer, not the primary control.
**Phase:** 6

### Decision: State-transition rule table is flat (one delta per classified label), not conditioned on current state
**Why:** Reaffirms the Phase 1 decision that buyer state updates are deterministic given LLM-classified behavior, not raw LLM-generated numbers. Conditioning deltas on current state too (e.g. "a close attempt lands differently depending on current trust") would reintroduce exactly the kind of harder-to-test, harder-to-reason-about complexity that decision was meant to avoid, for an MVP whose job is proving the loop works, not modeling nuanced buyer psychology.
**Alternatives considered:** State-conditional delta tables; letting the LLM propose a delta magnitude within a bounded range.
**Tradeoff:** Less "emergent" buyer behavior — every occurrence of the same classified behavior produces the same delta regardless of conversation history. Explicitly acceptable for Phase 6 per this phase's own prompt ("Do NOT invent a larger buyer-state system unless the existing project specification requires it"); revisit only with a demonstrated product reason, not by accretion.
**Phase:** 6

### Decision: LangGraph turn graph covers exactly one turn; looping/end-conditions are Phase 7's job
**Why:** `ARCHITECTURE.md` §4A sketches `check_end_conditions` (turn limit / patience threshold / explicit close) as part of the eventual conversation loop, but this Phase 6 prompt's PHASE BOUNDARY section explicitly rules out building Phase 7 features. `buyer/graph.py` therefore implements classify -> update_state -> generate_reply as a single straight-line graph with no loop-back edge; a future Phase 7 graph or plain Python loop calls `run_buyer_turn()` repeatedly and owns the termination decision.
**Alternatives considered:** Build the full multi-turn looping graph now, since the shape is already sketched in `ARCHITECTURE.md`.
**Tradeoff:** `buyer/graph.py` will need a Phase 7 caller before it's part of an actual playable conversation — but the turn logic itself is fully complete, tested, and callable in isolation now, which is what this phase's own PHASE BOUNDARY section calls for.
**Phase:** 6

### Decision: `MockLLMProvider` is a first-class, permanent part of the codebase, not a test-only throwaway
**Why:** The Phase 6 prompt requires zero API cost/key during development and a test suite that never depends on a real API. Rather than monkeypatching or mocking at the test-framework level, `MockLLMProvider` is a real implementation of the same `LLMProvider` protocol `AnthropicProvider` implements — so `buyer/service.py` and every node in the graph are provider-agnostic by construction, not just "happen to work with a mock because we patched something."
**Alternatives considered:** `unittest.mock.Mock()` / `pytest-mock` patches on an Anthropic client.
**Tradeoff:** Slightly more code (a real class with call recording, queued responses, failure simulation) than an ad hoc mock — but it's reusable across every test file, self-documents expected provider behavior, and the same abstraction is exactly what makes a real key swap-in-only later, per the phase requirement.
**Phase:** 6
