import type { Scenario } from "../types";

interface Props {
  scenario: Scenario;
  onBegin: () => void;
}

function BriefingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-4 border-t border-line py-3 first:border-t-0">
      <dt className="font-mono text-xs uppercase tracking-wider text-ink-faint">{label}</dt>
      <dd className="text-sm text-ink">{value}</dd>
    </div>
  );
}

export function StartScenario({ scenario, onBegin }: Props) {
  return (
    <main className="min-h-screen bg-bg px-4 py-16 text-ink">
      <div className="mx-auto max-w-xl">
        <p className="font-mono text-xs uppercase tracking-widest text-amber">Scenario Briefing</p>
        <h1 className="mt-2 font-display text-2xl font-semibold">{scenario.title}</h1>

        <dl className="mt-8 rounded-lg border border-line bg-surface px-6">
          <BriefingRow label="Persona" value={scenario.buyerPersona.name} />
          <BriefingRow label="Product" value={scenario.productContext} />
          <BriefingRow label="Known objection" value={scenario.knownObjection} />
          <BriefingRow label="Difficulty" value={scenario.difficulty} />
          <BriefingRow label="Turn limit" value={String(scenario.maxTurns)} />
        </dl>

        <p className="mt-6 text-sm leading-relaxed text-ink-muted">{scenario.buyerPersona.description}</p>

        <button
          onClick={onBegin}
          className="mt-10 w-full rounded-md bg-amber px-6 py-3 font-display text-sm font-semibold text-bg transition hover:bg-amber-dim"
        >
          Begin Assessment →
        </button>
      </div>
    </main>
  );
}
