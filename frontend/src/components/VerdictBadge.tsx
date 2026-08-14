import type { ReadinessVerdict } from "../types";

const verdictStyles: Record<ReadinessVerdict, { label: string; className: string }> = {
  READY: { label: "READY", className: "border-ready text-ready" },
  NOT_READY: { label: "NOT READY", className: "border-not-ready text-not-ready" },
  AT_RISK: { label: "AT RISK", className: "border-amber text-amber" },
};

export function VerdictBadge({ verdict }: { verdict: ReadinessVerdict }) {
  const style = verdictStyles[verdict];
  return (
    <span className={`inline-block rounded border px-3 py-1 font-display text-sm font-semibold tracking-wide ${style.className}`}>
      {style.label}
    </span>
  );
}
