import type { CompetencyEvaluation, ReadinessResult } from "../types";
import { EvidenceChip } from "../components/EvidenceChip";
import { VerdictBadge } from "../components/VerdictBadge";

interface Props {
  result: ReadinessResult;
  onRestart: () => void;
}

function CompetencyCard({ evaluation }: { evaluation: CompetencyEvaluation }) {
  const passed = evaluation.score >= evaluation.requiredMinScore;
  const exercised = evaluation.evidence.length > 0;

  return (
    <div className="rounded-lg border border-line bg-surface p-5">
      <div className="flex items-baseline justify-between">
        <h3 className="font-display text-sm font-semibold uppercase tracking-wide">
          {evaluation.displayName}
        </h3>
        <div className="flex items-baseline gap-2 font-mono text-sm">
          <span className={passed ? "text-ready" : exercised ? "text-not-ready" : "text-ink-faint"}>
            {exercised ? evaluation.score : "—"}
          </span>
          <span className="text-ink-faint">/ {evaluation.requiredMinScore} req.</span>
        </div>
      </div>

      <p className="mt-3 text-sm text-ink">{evaluation.diagnosis}</p>
      <p className="mt-1 text-sm text-ink-muted">{evaluation.impact}</p>

      {exercised && (
        <div className="mt-4 space-y-2">
          {evaluation.evidence.map((ev, i) => (
            <EvidenceChip key={i} evidence={ev} />
          ))}
        </div>
      )}

      <p className="mt-4 border-t border-line pt-3 text-sm text-amber">→ {evaluation.recommendation}</p>
    </div>
  );
}

export function Result({ result, onRestart }: Props) {
  return (
    <main className="min-h-screen bg-bg px-4 py-16 text-ink">
      <div className="mx-auto max-w-2xl">
        <p className="font-mono text-xs uppercase tracking-widest text-amber">Readiness Debrief</p>

        <div className="mt-3 flex items-center gap-4">
          <VerdictBadge verdict={result.verdict} />
        </div>
        <p className="mt-3 text-sm text-ink-muted">{result.reasoning}</p>

        <div className="mt-8 space-y-4">
          {result.evaluations.map((evaluation) => (
            <CompetencyCard key={evaluation.competencyKey} evaluation={evaluation} />
          ))}
        </div>

        <button
          onClick={onRestart}
          className="mt-10 rounded-md border border-line px-6 py-3 font-display text-sm font-semibold text-ink transition hover:border-amber hover:text-amber"
        >
          ← Run another assessment
        </button>
      </div>
    </main>
  );
}
