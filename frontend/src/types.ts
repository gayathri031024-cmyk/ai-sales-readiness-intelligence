// Mirrors DATA_MODEL.md. Mock data (src/mock/) and future real API
// responses (Phase 5+) both conform to these types, so swapping one
// for the other later is a data-source change, not a UI rewrite.

export type Difficulty = "easy" | "standard" | "hard";

export interface BuyerPersona {
  id: string;
  name: string;
  description: string;
}

export interface Scenario {
  id: string;
  title: string;
  buyerPersona: BuyerPersona;
  productContext: string;
  knownObjection: string;
  difficulty: Difficulty;
  maxTurns: number;
}

export type Sender = "rep" | "buyer";

export interface TranscriptMessage {
  id: string;
  turnIndex: number;
  sender: Sender;
  content: string;
}

// Phase 7 (Conversation Engine): the real conversation record from the
// backend. Deliberately has no hidden-state fields (trust/patience/
// budget_sensitivity/interest) — the backend never sends them, per
// ARCHITECTURE.md §6, so there is nothing to strip here.
export type ConversationStatus = "in_progress" | "completed";
export type ConversationEndReason = "turn_limit" | "patience_exhausted" | "explicit_close" | null;

export interface Conversation {
  id: string;
  scenarioId: string;
  status: ConversationStatus;
  endReason: ConversationEndReason;
  turnCount: number;
  maxTurns: number;
  messages: TranscriptMessage[];
}

export type CompetencyKey = "discovery" | "objection_handling" | "closing";

export interface Evidence {
  turnIndex: number;
  sender: Sender;
  quote: string;
  note: string;
}

export interface CompetencyEvaluation {
  competencyKey: CompetencyKey;
  displayName: string;
  score: number;
  requiredMinScore: number;
  diagnosis: string;
  impact: string;
  recommendation: string;
  evidence: Evidence[];
}

export type ReadinessVerdict = "READY" | "NOT_READY" | "AT_RISK";

export interface ReadinessResult {
  verdict: ReadinessVerdict;
  reasoning: string;
  evaluations: CompetencyEvaluation[];
}
