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

### Note: `app/readiness/` (`decision.py`/`schemas.py`/`service.py`) was found already present, uncommitted, at the start of Phase 9 — origin unknown, not trusted, independently verified
**What happened:** At the start of Phase 9, `backend/app/readiness/` already contained `decision.py`, `schemas.py`, and `service.py` — untracked in git, not present when Phase 8 inspected this same directory (it held only `__init__.py` then), and not something written earlier in this conversation. The code's own docstrings referenced "See DECISIONS.md, Phase 9" for reasoning that did not actually exist in this file at the time. Per the standing working rule ("do not trust filenames, previous chat claims, or assumptions"), this was treated as an unverified discrepancy, not adopted on sight.
**What I did:** Read the code against the actual DB schema (`db/models.py`) and every control document (ARCHITECTURE.md §3, MASTER_PROMPT.md's READINESS ENGINE section, DATA_MODEL.md's `readiness_results` table, `scenario/service.py`'s actual seeded thresholds) — it was structurally consistent with all of them, not fabricated. It was then proven correct by writing and running 24 real tests against it (`test_readiness.py`), not accepted on inspection alone. One real bug was found and fixed during that process, but it was in the *test fixture* (`.title()` mangling `"objection_handling"` into `"Objection_Handling"`), not in the found code itself.
**Why adopt it rather than rewrite from scratch:** Once independently verified against the schema, the docs, and a full passing test suite, rewriting equivalent code from scratch would have added risk (a second chance to introduce a bug) without adding confidence the found code didn't already have. The verification was the safeguard, not the authorship.
**Phase:** 9

### Decision: `AT_RISK_MARGIN = 10` points — the boundary between AT_RISK and NOT_READY
**Why:** MASTER_PROMPT.md, ARCHITECTURE.md, and DATA_MODEL.md all name the three verdicts (READY/NOT_READY/AT_RISK) but none specify a numeric margin distinguishing a "borderline" miss from a "clear" one. Rather than guess silently or leave the distinction unimplemented, 10 points was chosen as an explicit, documented, single named constant (`readiness/decision.py::AT_RISK_MARGIN`) — a competency missing its threshold by ≤10 points reads as AT_RISK; by more than 10, NOT_READY. Every failing competency's gap is compared against this same constant; the worst (largest) gap among failing competencies decides the verdict.
**Alternatives considered:** A percentage-of-threshold margin instead of a flat point value (rejected — flat points are simpler to reason about and to test, and the MVP thresholds are all in a similar 60-70 range where the two approaches wouldn't diverge much); requiring the CALLER (frontend) to interpret a raw gap rather than the backend naming a verdict at all (rejected — defeats the entire point of a deterministic backend rules engine per DECISIONS.md's Phase 1 entry).
**Tradeoff:** This is a placeholder judgment call, exactly like `scenario/service.py`'s own threshold values (60/70/65) — not calibrated against real transcripts yet. Same owner and same revisit trigger: Phase 15 (Stress Testing), if real conversations show this margin producing a nonsensical READY/AT_RISK/NOT_READY spread.
**Phase:** 9

### Decision: `readiness/` never triggers Phase 8's evaluation step itself, even lazily
**Why:** ARCHITECTURE.md §3's module boundary ("`readiness/` never calls an LLM") is stronger than just "doesn't call the LLM directly" — it also means readiness must never call *anything* that could transitively make an LLM call, including Phase 8's evaluation pipeline. `GET .../result` (the frontend's actual data source) computes-and-persists the readiness verdict lazily if evaluation has already run, but raises a clear error (404) rather than silently invoking `evaluation.service.evaluate_conversation` if it hasn't. The frontend is what sequences "evaluate, then fetch result" (see `frontend/src/api/readiness.ts`) — the same two steps a human operator would run by hand.
**Alternatives considered:** Have `GET .../result` transparently trigger evaluation too, for a single frontend call instead of two.
**Tradeoff:** One extra network round-trip from the frontend on first load of the Result screen, in exchange for a readiness module whose "never calls an LLM" guarantee is actually true of the whole call graph, not just the function you're looking at.
**Phase:** 9

### Decision: Readiness computation is idempotent by "does a `readiness_results` row already exist," and a repeat call never recomputes even though recomputing would be free
**Why:** Unlike Phase 8's idempotency (which also saves real LLM cost on a repeat call), a readiness recompute costs nothing — it's pure Python over already-persisted scores. It's still made idempotent, for a different reason: a verdict should reflect the evaluation as it stood when first decided. If a later phase (e.g. a Phase 8 re-evaluation feature) ever changes evaluation scores after the fact, a *stale* but *stable* readiness verdict is more trustworthy behavior than one that silently drifts underneath a rep who already saw it — that's a deliberate design decision to revisit explicitly, not an accident of "recompute would be free so why not."
**Alternatives considered:** Always recompute on every `POST .../readiness` call, discarding any prior row.
**Tradeoff:** No way to refresh a readiness verdict after evaluation scores change without a manual DB change — same class of tradeoff as Phase 8's evaluation idempotency, same "revisit if a real product need emerges" posture.
**Phase:** 9

### Decision: Frontend's `Result` screen consumed the existing `ReadinessResult`/`CompetencyEvaluation`/`Evidence` types unchanged — no `types.ts` edits needed
**Why:** Phase 4's original mock-data types (`verdict`, `reasoning`, `evaluations[]` with `competencyKey`/`displayName`/`score`/`requiredMinScore`/`diagnosis`/`impact`/`recommendation`/`evidence[]`) already matched the real `GET .../result` response shape field-for-field once adapted from snake_case. The one type-level mismatch — `Evidence.sender` — is handled by always setting it to `"rep"` in the adapter (`frontend/src/api/readiness.ts`) rather than adding a `sender` field to the wire format for a value that can only ever be one thing: Phase 8's `verify_evidence` structurally guarantees every persisted piece of evidence is rep-attributed (buyer-attributed evidence is deterministically rejected before persistence — see DECISIONS.md, Phase 8).
**Alternatives considered:** Add `sender` to the backend's `EvidenceOut` schema for symmetry with the frontend type.
**Tradeoff:** None identified — sending a field whose value the backend already guarantees is constant would just be redundant wire payload.
**Phase:** 9

### Note: `app/coaching/` (`priority.py`/`generation.py`/`verification.py`/`schemas.py`/`service.py`), `api/routes/coaching.py`, the `coaching_sessions` migration, and the `CoachingSession` model/relationship were found already present, uncommitted, at the start of Phase 10 — same situation as Phase 9's `readiness/` discovery, handled the same way
**What happened:** At the start of Phase 10, this entire module already existed on disk, untracked in git, not present in the Phase 9 checkpoint's committed tree (`b2edc18`). Per the same standing working rule applied at the start of Phase 9, this was not adopted on sight.
**What I did:** Stashed the found work (`git stash -u`) to re-verify the actual Phase 9 baseline (144 tests) in isolation first, then restored it and read every file against the actual DB schema, `readiness/decision.py`'s existing `CompetencyResult` dataclass (correctly reused rather than duplicated), and every relevant control document (MASTER_PROMPT.md's COMPETENCY/SKILL GRAPH and TRAINING LOOP sections, DATA_MODEL.md's explicit deferral of `coaching_sessions` to "phase 10" by name, PHASE_0_PRODUCT_STRATEGY.md's Milestone 2 scope table). It was structurally consistent with all of them and correctly reused Phase 8/9 architecture rather than duplicating it (evidence-id grounding mirrors Phase 8's turn_index approach exactly; priority selection reuses `readiness/decision.py::CompetencyResult` directly). Then proven correct by running the found 23-test suite (`test_coaching.py`) — all passed on the first run, no fixture bugs this time. Also independently verified the migration chains correctly from the actual current head and produces the exact expected schema against a fresh DB.
**Why adopt it rather than rewrite from scratch:** Same reasoning as Phase 9's note above — once independently verified against the schema, the docs, and a passing test suite, the verification is the safeguard, not the authorship.
**Phase:** 10

### Decision: Coaching priority (which competency to focus on) is picked deterministically, before the LLM is ever called — the LLM writes about the pick, never makes it
**Why:** Rule 12 of this phase ("preserve the deterministic readiness decision engine") and MASTER_PROMPT.md's own COMPETENCY/SKILL GRAPH section ("must not claim causality without evidence") both point the same direction: which competency matters most is a comparison of already-persisted numbers (score vs. threshold, from Phase 8/9), not a judgment call for the model to make. `coaching/priority.py::pick_priority` reuses `readiness/decision.py`'s own `CompetencyResult` dataclass rather than inventing a second, slightly different one — if any competency failed its threshold, the one with the largest gap is picked (most impactful to fix first); if every competency passed (a READY conversation), the one with the narrowest passing margin is picked (closest to slipping). Ties break on the fixed MVP competency order, so the pick is always fully deterministic. The LLM (`generation.py`) is handed this pick and explicitly instructed not to override it.
**Alternatives considered:** Let the LLM choose which competency to prioritize, given all three scores (rejected — this is exactly the kind of decision Phase 9 established should never be delegated to the model); a full dependency-graph root-cause engine (e.g., "weak closing traced back to weak discovery") as MASTER_PROMPT.md's skill-graph language gestures at — explicitly out of scope, since that requires `skill_graph_edges` (Phase 14, not yet built) and would be exactly the "full skill graph with dependency modeling" ARCHITECTURE.md explicitly deferred past Milestone 1/2.
**Tradeoff:** No cross-competency causal reasoning yet (e.g., explaining that weak discovery evidence likely contributed to a weak closing score) — the priority pick and its stated reason are both single-competency facts (its own gap or margin), not a multi-competency causal claim. This is intentional, not an oversight: MASTER_PROMPT.md's own language is "the system may propose root causes... but must not claim causality without evidence," and there is no evidence linking one competency's shortfall to another's without the skill graph Phase 14 will build. Revisit then.
**Phase:** 10

### Decision: Coaching points must cite a real `evidence_id` (or explicitly cite none) — the same "propose vs. decide" split as Phase 8's evidence extraction/verification pair, applied one layer up
**Why:** Rule 15 of this phase ("prevent hallucinated coaching claims unsupported by persisted evidence") is the coaching-layer analogue of Phase 8's evidence-hallucination invariant. Rather than re-deriving grounding from the raw transcript (which the coaching LLM never sees), `coaching/verification.py` checks the model's cited `evidence_id` against the exact set of already-verified `Evidence` row ids it was shown for that competency — a coaching point can only reference evidence that Phase 8 already proved was really said. A point with no `evidence_id` at all (general encouragement, or coaching about a competency with no evidence) always passes through unchanged; a point citing a real id from the *wrong* competency, or a fabricated id, is silently dropped.
**Alternatives considered:** Let the coaching LLM re-quote from the raw transcript directly (rejected — reopens exactly the hallucination surface Phase 8's `verify_evidence` was built to close, and gives the coaching layer transcript access it doesn't need); trust the model's evidence_id without re-checking it (rejected — identical reasoning to Phase 8's own verification step).
**Tradeoff:** None identified — this is strictly additive safety on top of data the coaching prompt already had to include anyway.
**Phase:** 10

### Decision: Coaching never triggers Phase 9's readiness computation itself, even lazily — same module-boundary discipline as `readiness/` never triggering Phase 8's evaluation
**Why:** Direct continuation of the Phase 9 decision by the same name. `coaching/service.py::compute_and_persist_coaching` requires `conversation.readiness_result` to already exist and raises a clear 409 if it doesn't, rather than silently computing it. Each phase's service module only ever reads the prior phase's already-persisted output — it never reaches backward to compute it.
**Alternatives considered:** Have `POST .../coaching` transparently chain readiness (and even evaluation) computation for a single-call frontend convenience, the same tradeoff Phase 9 considered and declined for `/result`.
**Tradeoff:** Same as Phase 9's — an extra round-trip is left to whatever consumes this API (frontend or otherwise) in exchange for every module's "never calls anything upstream automatically" guarantee holding for the whole call graph, not just the function you're looking at.
**Phase:** 10

### Decision: Coaching is idempotent by "does a `coaching_sessions` row already exist" — same posture as readiness, not evaluation
**Why:** Mirrors `readiness/service.py`'s reasoning exactly (see DECISIONS.md, Phase 9): a coaching session, once generated, is treated as authoritative for that conversation rather than silently regenerated — consistent behavior for a rep who already read their coaching, and it avoids an unnecessary repeat LLM call on top of that.
**Alternatives considered:** Always regenerate on every `POST .../coaching` call.
**Tradeoff:** No way to regenerate coaching after the fact without a manual DB change — same class of tradeoff and same "revisit only if a real need emerges" posture as Phase 8's and Phase 9's identical decisions.
**Phase:** 10

### Decision: Frontend not touched this phase — coaching is API-only for now
**Why:** Unlike Phase 9 (where the Phase 4 mock types already matched the real API shape with zero changes needed), a coaching UI is a genuinely new piece of screen real estate — there is no existing mock/type/screen for it to slot into, and no control document mandates a specific coaching UI design for this phase. Building one now would mean inventing UI/UX scope (what a coaching card looks like, where it sits relative to the readiness verdict, whether points are grouped by competency) that no control document specifies — exactly the kind of unspecified requirement rule 10 of this phase says not to guess at. The backend API is complete, tested, and reachable (`POST`/`GET /conversations/{id}/coaching`) for a future phase — or an explicit follow-up instruction — to wire up.
**Alternatives considered:** Add a minimal coaching card to `Result.tsx` now, following the same shape as the existing evaluation cards.
**Tradeoff:** The founder-demo user journey (conversation → evaluation → readiness → coaching) is not yet visually complete in the browser. Recorded in KNOWN_ISSUES.md for explicit review, not decided unilaterally.
**Phase:** 10

### Decision: Targeted Drills makes zero LLM calls — a third precedent for "prefer deterministic logic over LLM calls wherever possible," now for an entire phase, not just a fallback path
**Why:** MASTER_PROMPT.md's TRAINING LOOP names the step this phase builds ("Weakness → **targeted drill** → practice → reassessment → competency achieved") but specifies no content requirements for a drill beyond what "targeted" implies — which competency, and why. Every fact a drill could need already exists, already verified: Phase 9's deterministic priority pick (via `readiness/decision.py::CompetencyResult`, reused directly — not duplicated — by `coaching/priority.py`), Phase 8's evaluation diagnosis/recommendation for that competency, and Phase 10's already-grounded coaching points (already checked against real evidence ids by `coaching/verification.py`). Asking an LLM to write about the same facts a third time would add cost and a fresh hallucination surface for zero new information. `drills/generation.py` is pure Python reassembly — trivially unit-testable, and structurally incapable of introducing a claim Phase 8/10 didn't already verify, because it has no path to introduce anything at all.
**Alternatives considered:** An LLM call to turn the same inputs into friendlier prose (rejected — the coaching session, one phase upstream, already produced friendly, evidence-grounded prose; a drill re-phrasing the same facts a third time is marginal value for a new hallucination and cost surface); a fully separate "practice instructions" LLM prompt with its own tone/voice (rejected for the same reason, plus rule 15's "prevent hallucinated coaching claims unsupported by persisted evidence" is trivially satisfied — zero new claims are possible — rather than merely well-defended).
**Tradeoff:** Drill instructions read as a direct assembly of already-existing text rather than fresh, tailored prose — noticeably more "templated" than Phase 10's coaching narrative. Acceptable for MVP; revisit if user feedback specifically asks for more natural-reading drill instructions once there's a real product to get that feedback from.
**Phase:** 11

### Decision: "Targeted" means competency-focused, not scenario-generated — `practice_scenario_id` is always the origin conversation's own scenario
**Why:** The MVP has exactly one seeded scenario (`scenario/service.py`'s `_MVP_COMPETENCIES` seeding, unchanged since Phase 5) — there is no scenario library, no scenario-authoring capability, and no control document describes one existing before this phase. A drill cannot "target" a different scenario that doesn't exist. What Phase 11 can legitimately target, and does, is which competency the rep should focus on when they practice again — the drill's `competency_id`, `focus_reason`, `instructions`, and filtered `focus_points` are all genuinely competency-specific and evidence-grounded, even though the practice scenario itself is necessarily the same one. `practice_scenario_id` exists on the `Drill` row specifically so a future multi-scenario phase can start choosing a *different* scenario without a schema change — the field is forward-compatible even though its value is currently always identical to `conversation.scenario_id`.
**Alternatives considered:** Omit `practice_scenario_id` entirely until a real scenario library exists (rejected — would require a breaking schema change later for no present benefit); invent a second scenario now to make "targeted" feel more literal (rejected outright — exactly the kind of "do not guess or fabricate requirements" rule 10 warns against; no control document asks for scenario variation in this phase, and scenario authoring is unspecified, non-trivial product scope).
**Tradeoff:** "Targeted drill" in this MVP is honestly a narrower claim than the phrase might suggest to a reader expecting a bespoke practice scenario — it's the same conversation shape, refocused by explicit instructions rather than by a different underlying scenario. Documented here and in KNOWN_ISSUES.md rather than left implicit.
**Phase:** 11

### Decision: Reassessment (the fourth step of MASTER_PROMPT.md's training loop — "drill → practice → **reassessment** → competency achieved") is explicitly out of Phase 11's scope, not silently folded in
**Why:** `DATA_MODEL.md` lists `drills` and `reassessments` as two separate deferred tables, not one — implying two distinct pieces of schema/logic, not that "reassessment" is just a drill sub-feature. The phase is named "Targeted Drills," not "Targeted Drills & Reassessment," in every control document that names it (MASTER_PROMPT.md's phase table, `PROJECT_PLAN.md`). Building reassessment now — linking a fresh practice conversation back to a specific drill, then comparing before/after evaluation scores — is a genuinely new cross-cutting mechanism with zero column-level specification anywhere in the control documents beyond the bare table name `reassessments`, and rule 9 of this phase is explicit: do not guess missing requirements. A rep can already practice again today, for free, using the existing `POST /conversations` flow and the drill's `practice_scenario_id` — what's missing for a real reassessment *loop* is the explicit link-back-and-compare mechanism, which this phase does not invent.
**Alternatives considered:** Add a nullable `origin_drill_id` FK to `Conversation` now, so a future phase has less schema work to do (rejected — speculative schema for a mechanism with no specified comparison/completion logic yet is exactly the "premature infrastructure the Product Scope Gate exists to prevent" language `DATA_MODEL.md`'s own scope check uses); build a minimal reassessment table now with just a `drill_id` + `new_conversation_id` pair and nothing else (rejected — a table with no defined "reassessment complete" semantics would just be dead schema, worse than no table at all).
**Tradeoff:** The training loop MASTER_PROMPT.md describes is not fully closed by Phase 11 alone — a rep gets a targeted drill telling them what to practice and why, but the system does not yet automatically detect that a later conversation was "the reassessment" for that drill, or automatically confirm the competency was fixed. Recorded explicitly in KNOWN_ISSUES.md as an open boundary, owner: a dedicated future phase (not yet numbered in the roadmap beyond "Phase 12 — Adaptive Difficulty," which is not the same concept).
**Phase:** 11

### Decision: Drill is idempotent by "does a `drills` row already exist" — same posture as readiness/coaching, for consistency reasons rather than cost reasons
**Why:** Unlike readiness (deterministic, free) and coaching (one real LLM call, real cost), a drill regenerate would also be free — yet it's still made idempotent, purely for the same behavioral-consistency reason `readiness/service.py`'s identical decision gives: a drill a rep already started reading shouldn't silently change under them mid-practice. Consistency of user-facing behavior, not cost avoidance, is the actual reason here — worth stating plainly since the usual "save an LLM call" justification doesn't apply to a zero-LLM module.
**Alternatives considered:** Regenerate on every `POST .../drill` call, since it's free to do so.
**Tradeoff:** No way to refresh a drill after coaching changes (e.g., if a future phase allows re-coaching) without a manual DB change — same class of tradeoff, same "revisit only if a real need emerges" posture as every idempotency decision in Phases 9/10.
**Phase:** 11

### Decision: Frontend not touched this phase either
**Why:** Same reasoning as Phase 10's identical decision, one level further down the same unbuilt UI chain — a drill card would sit downstream of a coaching card that doesn't exist yet in the frontend. Building drill UI without coaching UI first would be building on top of nothing; building both now would mean inventing two full unspecified UI/UX designs in one phase, against rule 10.
**Alternatives considered:** None seriously considered — this follows directly from the unresolved Phase 10 frontend decision rather than being a fresh choice.
**Tradeoff:** Same as Phase 10's — recorded in KNOWN_ISSUES.md, not decided unilaterally.
**Phase:** 11
