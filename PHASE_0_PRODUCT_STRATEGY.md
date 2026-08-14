# PHASE 0 — PRODUCT STRATEGY

**Project:** AI Sales Readiness Intelligence
**Phase:** 0 — Product Strategy
**Status:** Draft, awaiting review (CHECKPOINT PASSED required to proceed)

---

## 1. Target User

**Primary:** Individual sales rep (SDR/AE) preparing for a specific upcoming customer conversation.
**Secondary (post-MVP):** Sales manager who needs visibility into team readiness and skill gaps.

The MVP is built entirely for the primary user. The manager view is explicitly deferred (see Scope Gate).

## 2. Buyer Personas (for the AI Buyer)

A small, deliberately narrow starting set — enough to prove the adaptive-state concept without building a persona library:

| Persona | Sophistication | Primary Concern | Typical Objection |
|---|---|---|---|
| Enterprise CFO | High | ROI, risk, budget cycle | Price / implementation cost |
| SMB Owner | Medium | Time, simplicity | "Too complicated for us" |
| Skeptical Technical Buyer | High | Integration, security | "Does this actually work with X?" |

MVP ships with **one** fully-built persona (Enterprise CFO) end-to-end; the other two are stretch goals once the loop is proven.

## 3. Salesperson Personas (who uses it)

- New rep needing repeatable practice before first real calls
- Experienced rep prepping for one specific, high-stakes meeting tomorrow
- Rep who lost a real deal and wants to understand why, using a reconstructed scenario

## 4. Jobs-to-be-Done

> "When I have an important sales call coming up, I want to practice against a realistic, resistant version of that specific buyer, so that I walk in already knowing where my pitch breaks down — instead of finding out live, with revenue on the line."

## 5. Problem Statement

Reps mostly learn through mistakes made in front of real prospects — an expensive way to learn. Generic sales training doesn't map to the specific customer, product, and objection a rep is about to face. Managers usually see *that* a rep is struggling, but not *why*, and have no mechanism to close a specific gap before the next call happens.

## 6. Core User Journey (MVP)

```
"Prepare me for tomorrow's Enterprise CFO meeting"
              ↓
System generates scenario (persona, product, objection, difficulty)
              ↓
Rep roleplays against Adaptive AI Buyer (text chat)
              ↓
Conversation ends (rep closes, buyer disengages, or time/turn limit)
              ↓
Evidence-based evaluation across a small competency set
              ↓
Deterministic readiness decision, with evidence shown
```

No coaching, drills, or reassessment in this journey yet — those are Milestone 2.

## 7. MVP Boundary — Product Scope Gate

| Feature | Classification |
|---|---|
| Single scenario definition (persona + product + objection) | **MUST HAVE** |
| Adaptive AI Buyer with explicit hidden state (trust, patience, budget sensitivity — 3–4 dimensions, not 7+) | **MUST HAVE** |
| Text conversation engine, turn-based, persisted | **MUST HAVE** |
| Evidence extraction (timestamped, tied to actual transcript lines) | **MUST HAVE** |
| Evaluation across 3–4 competencies (Discovery, Objection Handling, Closing) | **MUST HAVE** |
| Deterministic, scenario-specific readiness engine (READY / NOT READY / AT RISK) | **MUST HAVE** |
| Minimal persistence + single-user auth (or no-auth prototype mode) | **MUST HAVE** |
| Root-cause analysis across a skill graph | SHOULD HAVE (Milestone 2) |
| Personalized coaching generation | SHOULD HAVE (Milestone 2) |
| Targeted drill generation + reassessment loop | SHOULD HAVE (Milestone 2) |
| Adaptive difficulty | SHOULD HAVE (Milestone 2) |
| Product/company RAG (document upload, grounded answers) | LATER (Milestone 3) |
| Full skill graph with dependency modeling across 7 competencies | LATER (Milestone 3) |
| Manager dashboard / team rollups | LATER (Milestone 3) |
| AI evaluation benchmark suite | LATER (Milestone 3) |
| Multi-tenant org isolation, full security hardening | LATER (Milestone 3) |
| Production deployment, cost tuning | LATER (Milestone 3) |
| Voice (speech-to-text / text-to-speech) | **DO NOT BUILD** until everything above is excellent — treat as optional, not a goal |
| Multiple AI agents / agent orchestration frameworks beyond one LangGraph app | **DO NOT BUILD** |
| Microservices / Kubernetes | **DO NOT BUILD** |
| CRM/calendar/dialer integrations | **DO NOT BUILD** |
| Multi-language / code-mixing support | **DO NOT BUILD** |
| Mobile app | **DO NOT BUILD** |

## 8. Non-MVP Scope (explicit exclusions for now)

Everything marked SHOULD HAVE, LATER, or DO NOT BUILD above. In particular: no RAG, no manager view, no voice, no multi-persona library, no multi-tenant security model. These are real roadmap items (Phases 10–21) but do not block Milestone 1.

## 9. Differentiation

The pitch is not "we built an AI sales chatbot." Existing tools (e.g. Cuebo) already do realistic roleplay, scoring, and coaching well, with real customers and published outcomes. This project's differentiation is narrower and deeper:

- **Every score has evidence** — no opaque numbers.
- **The LLM never decides readiness** — a deterministic, inspectable rules engine does, using LLM-supplied evidence as input.
- **Root cause over symptom** (Milestone 2) — a low closing score is explained in terms of upstream discovery/value gaps, not treated as an isolated failure.
- Built to be **explainable to a technical founder**, not just demoed.

## 10. Product Principles

1. Every evaluation must show evidence, not just a number.
2. The LLM proposes; deterministic logic decides readiness.
3. Text before voice — voice adds cost and complexity without proving the concept.
4. One excellent loop beats ten mediocre features.
5. No fabricated business outcomes; any results shown are clearly labeled synthetic/prototype data.
6. Explainability beats cleverness — every architectural choice must be defensible in a conversation.

## 11. Success Metrics (for a prototype — not a live business)

Since there are no real customers, metrics measure the *system's* soundness, not business impact:

- Loop completion rate: can a fresh scenario reliably produce a valid, evidence-backed readiness decision?
- Evaluator consistency: scoring variance when the same transcript is evaluated multiple times
- Hidden-state leakage rate: does the buyer ever reveal internal state values directly?
- Time to demo: can a first-time viewer understand the product's value within 2 minutes?

Explicitly **not** claimed: ramp-time reduction, conversion lift, or any real revenue outcome — those require real customers and are out of scope for a portfolio project.

## 12. Founder Demo Strategy

Two-minute flow: "Prepare me for tomorrow's Enterprise CFO meeting" → live roleplay against the adaptive buyer → conversation ends → evidence-based evaluation shown on screen → deterministic readiness verdict with reasoning. Close by walking through the architecture and explicitly naming the engineering decisions (deterministic readiness gate, structured-output validation, hidden buyer state) that a technical founder would probe.

---

## Phase 0 Output Rule — Required Answers

1. **What we are building:** The smallest convincing version of Scenario → Adaptive AI Buyer → Conversation → Evidence → Evaluation → Readiness, for one buyer persona and 3–4 competencies.
2. **What we are NOT building (yet):** RAG, manager dashboard, voice, root-cause/coaching/drills, adaptive difficulty, multi-tenant security, production deployment.
3. **Why the MVP is valuable:** It proves the two hardest, most differentiating parts of the whole product — a genuinely stateful adaptive buyer, and evidence-based deterministic evaluation — without time spent on scaffolding that doesn't test the core hypothesis.
4. **What makes it technically defensible:** Explicit state machine (not prompt-only) for the buyer; structured-output validation on every LLM call; a deterministic rules engine (not an LLM) makes the final readiness call; evidence is tied to actual transcript lines, not invented.
5. **What can be demonstrated in 2 minutes:** One full scenario run — roleplay, evaluation, and readiness verdict with evidence — start to finish.
6. **What could cause the project to fail:** Evaluator inconsistency (same behavior scored differently across runs); buyer leaking hidden state directly; evidence extraction hallucinating quotes not actually in the transcript; scope creep before Milestone 1 is solid.
7. **Assumptions that must be validated before Milestone 1 is "done":**
   - The LLM can maintain hidden buyer state across a conversation without leaking it.
   - Structured-output evidence extraction stays faithful to the actual transcript (no hallucinated quotes).
   - A small, fixed rubric produces reasonably consistent scores across repeated runs of the same transcript.
   - Deterministic thresholds feel legible and fair to a human reviewing the readiness verdict.

---

## PHASE 0 CHECKPOINT

**Objective:** Define product strategy and MVP boundary before any implementation.
**Completed:** Product strategy document produced; MVP scope classified via Product Scope Gate; assumptions to validate identified.
**Files Created/Modified:** `PHASE_0_PRODUCT_STRATEGY.md`, `PROJECT_STATE.md` (initialized)
**Architecture Changes:** None — no code written this phase, per Phase 0 Output Rule.
**Tests Performed:** N/A (no implementation yet)
**Acceptance Criteria:** Strategy doc covers target user, personas, JTBD, problem statement, journey, MVP boundary, differentiation, principles, metrics, demo strategy; scope gate applied; 7 output-rule questions answered.
**Known Problems:** None yet — pending your review of the scope decisions (P3: persona list may be too narrow/broad, open to adjustment).
**Technical Debt:** None.
**Manual Verification:** Read this document. Confirm or challenge the MVP boundary, especially anything marked MUST HAVE you think should move to SHOULD HAVE/LATER, or vice versa.
**Expected Result:** You either approve the scope or push back on specific items.
**Regression Test:** N/A.
**Decision:** PASS (recommended) — **pending your review**

---

**STOP.** Waiting for `CHECKPOINT PASSED` before starting Phase 1 — System Architecture.
