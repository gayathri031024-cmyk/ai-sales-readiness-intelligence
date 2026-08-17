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

### Decision: The rep always speaks first — no scripted opening buyer line
**Why:** Phase 6's buyer engine (`run_buyer_turn`) always classifies a rep message before generating a reply; there is no ungated "just say something" path. Inventing one solely to produce a scripted conversation-opener would be exactly the kind of Phase 6 redesign this phase's PHASE BOUNDARY section rules out. The Phase 4 mock UI showed the buyer speaking first (a canned opening line), but that was placeholder UX built before the real buyer engine existed.
**Alternatives considered:** Add a separate "opening line" code path that calls response generation directly, skipping classification and state update, seeded from `scenario.known_objection`.
**Tradeoff:** The live experience now opens on a blank transcript with a one-line UI hint ("the conversation starts with you") rather than the buyer immediately posing an objection. This is a legitimate product UX question for review, not a technical limitation — worth revisiting explicitly if the reviewed experience feels wrong, but not invented unilaterally here.
**Phase:** 7

### Decision: `conversations.status` stays exactly `in_progress` / `completed` (no third `failed` status)
**Why:** `DATA_MODEL.md` already establishes exactly these two status values. The Phase 7 spec's own sketch ("active" / "completed" / "failed") is looser language, not a hard requirement, and explicitly defers to "whatever status terminology the project already establishes." Introducing a third status would be an unrequested schema/vocabulary change.
**Alternatives considered:** Add `status = "failed"` for the patience-exhausted case, mirroring the "failed" wording used loosely in the Phase 7 prompt text.
**Tradeoff:** A patience-exhausted conversation and a turn-limit conversation are both `status: completed`, distinguished only by `end_reason`. This is arguably clearer, not a compromise — `end_reason` already exists in the data model specifically to carry that distinction (`turn_limit` / `patience_exhausted` / `explicit_close`), so a second status axis would be redundant.
**Phase:** 7

### Decision: Patience-exhausted end condition triggers at the state model's own clamp floor (`patience <= 0`), not a new arbitrary threshold
**Why:** `BuyerState` already defines `[0, 100]` as the bounded range for every dimension (Phase 6). Using the schema's own floor as the "buyer has walked away" signal ties this end condition to an existing, tested boundary rather than inventing a second number (e.g. "patience <= 15") that would need its own justification and calibration.
**Alternatives considered:** A configurable per-scenario patience threshold (e.g. a new `scenarios.patience_floor` column).
**Tradeoff:** Every scenario currently shares the same implicit floor (0) regardless of persona sophistication. Acceptable for the single MVP scenario; a future scenario-authoring phase (per DATA_MODEL.md's deferred-entities list) is the natural place to make this configurable if a second scenario ever needs a different bar.
**Phase:** 7

### Decision: Default single-user via an idempotent `get_or_create_default_user`, not a new auth system
**Why:** `conversations.user_id` is a required FK (Phase 2 decision, made specifically so multi-user support later doesn't require a migration). ARCHITECTURE.md §8 explicitly defers multi-user auth to Milestone 3. Rather than leaving `user_id` unset or building any auth, `conversation/service.py` reuses the exact idempotent-lookup-or-create pattern `scenario.service.seed_mvp_scenario` already established.
**Alternatives considered:** A minimal auth stub (API key header, single hardcoded user id passed by the frontend).
**Tradeoff:** Every conversation in this MVP sandbox is attributed to the same synthetic user regardless of who is actually typing — acceptable since there is no multi-user requirement yet, and the schema doesn't need to change when real auth is eventually added.
**Phase:** 7

### Decision: Turn submission response returns the full `ConversationOut` (messages included), not a narrower "just the buyer's reply" shape
**Why:** ARCHITECTURE.md §6 already commits to "frontend always re-fetches rather than trusting local history, so a refresh never desyncs from the server record." Returning the full conversation state from every mutating endpoint (`start`, `send turn`, `close`) means the frontend has exactly one shape to render everywhere and never has to reconcile a partial turn response against previously-fetched state.
**Alternatives considered:** A narrow `{buyer_reply: str}` response, requiring a separate `GET` to refresh full state after every turn.
**Tradeoff:** Slightly larger response payloads (the full transcript on every turn) in exchange for a strictly simpler frontend state model and one less network round-trip per turn.
**Phase:** 7

### Decision: Evidence candidates reference `turn_index` (an integer already shown in the transcript), never a raw `message_id` (a UUID)
**Why:** Asking the model for a UUID it was never shown would just invite a different flavor of hallucination — it could only ever copy or invent one. `evaluation/verification.py` deterministically maps the model's `turn_index` back to the real `messages.id` FK in code, so the model never gets to fabricate that identifier either. This mirrors the Phase 1 "LLM proposes, deterministic logic decides" principle at the identifier level, not just the content level.
**Alternatives considered:** Ask the model to output the real `message_id` directly.
**Tradeoff:** One extra deterministic lookup step; in exchange, an entire class of "evidence points at a message that doesn't exist" bugs is structurally impossible rather than merely unlikely.
**Phase:** 8

### Decision: Evidence must be grounded in a REP message, never a BUYER message — enforced both in the extraction prompt and, independently, in deterministic verification
**Why:** The competencies being scored (discovery, objection_handling, closing) are about the rep's demonstrated behavior. A quote from the buyer, even if verbatim-accurate, cannot be evidence of what the *rep* did. Checking `message.sender == "rep"` in `verify_evidence` — not just instructing the model not to do this — closes the gap between "the model was told not to" and "the system cannot persist it even if the model does anyway," the same defense-in-depth pattern already used for buyer-state leakage (see Phase 6 decisions above).
**Alternatives considered:** Trust the prompt instruction alone; allow buyer-message evidence with a `sender` field on the Evidence record for context.
**Tradeoff:** A small amount of legitimate context (e.g., "the buyer explicitly thanked the rep for X") can never be cited as evidence under this rule — acceptable, since the evaluation is scoped to rep competency, not buyer sentiment.
**Phase:** 8

### Decision: Competency scoring skips the LLM entirely (deterministic result) when a competency has zero verified evidence, or when scoring genuinely fails after `call_structured`'s retry
**Why:** MASTER_PROMPT.md's COST section: "prefer deterministic logic over LLM calls wherever possible." There is nothing for the model to interpret when there's no evidence, and asking it to score an empty evidence set risks it inventing a plausible-sounding number for behavior that was never observed. The two deterministic fallbacks (`no_evidence_result` / `unavailable_result`) are worded differently so a rep or reviewer can tell "you didn't demonstrate this" apart from "this couldn't be scored" — see `evaluation/scoring.py`.
**Alternatives considered:** Always call the LLM per competency, including with an empty evidence list, and let it output a 0 with generic text.
**Tradeoff:** Two fixed deterministic templates instead of always-fresh model prose for these two cases — judged acceptable since neither case has any real signal to phrase originally, and it directly reduces AI cost/hallucination surface per the phase's own instruction to prefer determinism.
**Phase:** 8

### Decision: Hidden buyer state never enters any Phase 8 prompt (extraction or scoring), at all
**Why:** Same structural reasoning as the Phase 6 decision "numeric buyer state never enters the reply-generation prompt" — the primary control against leaking something is not including it in what the model receives in the first place. Evaluation is about observable rep behavior in the transcript, not the buyer's hidden mechanics, so there was never a reason for either Phase 8 prompt to reference trust/patience/budget_sensitivity/interest, even as qualitative hints.
**Alternatives considered:** N/A — no version of this phase's design ever needed hidden state in these prompts.
**Tradeoff:** None identified.
**Phase:** 8

### Decision: `POST /conversations/{id}/evaluate` (trigger, idempotent) + `GET /conversations/{id}/evaluation` (fetch), not ARCHITECTURE.md §5's original `/complete` + `/result` sketch
**Why:** Continues the Phase 7 precedent of diverging from that early sketch where later phases clarified the naming: "complete" is already Phase 7's `/close` endpoint, and "/result" would imply a bundled readiness verdict — which this phase's PHASE BOUNDARY explicitly excludes. Two verbs on the same resource (`evaluate`/`evaluation`) mirrors the existing `POST /conversations` vs. `GET /conversations/{id}` pattern.
**Alternatives considered:** Reuse `/close` to also trigger evaluation as a side effect (rejected — conflates two distinct actions with two distinct failure modes); a single `/result` endpoint that returns partial data (evaluation only) until Phase 9 adds the verdict (rejected — a `ReadinessResult`-shaped response with no verdict is a worse contract than a clearly-scoped `ConversationEvaluationOut`).
**Tradeoff:** Frontend's `Result` screen (Phase 4 mock) still cannot be fully wired to real data until Phase 9 adds a readiness endpoint — surfaced as a known limitation below, not resolved unilaterally by inventing a partial/fake verdict this phase.
**Phase:** 8

### Decision: Evaluation is idempotent by "any existing rows for this conversation" rather than a soft-delete/versioning scheme
**Why:** The pipeline always writes all three MVP competency evaluations together in one transaction (see `evaluate_conversation`), so "at least one row exists" is a reliable proxy for "this conversation was already evaluated." Re-running `POST .../evaluate` returns the existing rows unchanged rather than re-extracting/re-scoring — avoiding both duplicate rows (the `(conversation_id, competency_id)` unique constraint would reject a naive re-insert anyway) and unnecessary repeat LLM calls, per the COST section.
**Alternatives considered:** A `force=true` re-evaluation query param; versioned evaluation rows (`evaluations.version`) allowing history.
**Tradeoff:** No way to re-run evaluation on the same conversation without a manual DB change — acceptable for MVP; revisit only if a real product need for re-evaluation (e.g., after a scoring-rubric change) emerges later.
**Phase:** 8

### Decision: Frontend not touched this phase — `Result` screen stays on mock data
**Why:** Inspecting `frontend/src/types.ts` and `screens/Result.tsx` (per this phase's "inspect existing frontend architecture" instruction) shows the Phase 4 `ReadinessResult` type bundles the Phase 8 evaluation data (`evaluations`) together with the Phase 9 readiness verdict (`verdict`/`reasoning`) into a single object, and the screen renders both together (each competency card shows score against `requiredMinScore`, a threshold comparison that is itself Phase 9 readiness logic). Wiring the screen to real Phase 8 data now would require either fabricating a placeholder verdict (a Phase 9 concept this phase must not implement) or splitting the type/screen into two pieces ahead of Phase 9 actually needing that split — both go beyond "if frontend work is NOT required by the Phase 8 control documents, do not invent unnecessary UI scope."
**Alternatives considered:** Split `ReadinessResult` into `ConversationEvaluationOut`-shaped data (real, Phase 8) + a still-mocked verdict; wire evaluation data into `Result` with a placeholder "verdict pending" state.
**Tradeoff:** `Result` remains on Phase 4 mock data for one more phase. Real Phase 8 data is fully available and tested via the API (`POST/GET .../evaluate(ion)`) for Phase 9 to consume alongside the real readiness decision, in one coherent frontend change rather than two partial ones. Recorded in KNOWN_ISSUES.md for your review.
**Phase:** 8
