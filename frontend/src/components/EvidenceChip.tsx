import type { Evidence } from "../types";

/**
 * Signature element of the product's UX: every evidence citation is
 * anchored to a real turn number, styled like a transcript reference
 * rather than a decorative quote block. This is deliberate — it's the
 * visual proof of the "every score has evidence" product principle,
 * not just a styling choice.
 */
export function EvidenceChip({ evidence }: { evidence: Evidence }) {
  const senderLabel = evidence.sender === "buyer" ? "BUYER" : "REP";
  const senderColor = evidence.sender === "buyer" ? "text-ink-muted" : "text-rep";

  return (
    <div className="flex gap-3 rounded border border-line bg-surface px-3 py-2">
      <div className="shrink-0 pt-0.5 font-mono text-xs text-ink-faint">
        T{String(evidence.turnIndex).padStart(2, "0")}
      </div>
      <div className="min-w-0">
        <p className="font-mono text-xs">
          <span className={senderColor}>{senderLabel}</span>{" "}
          <span className="text-ink">&ldquo;{evidence.quote}&rdquo;</span>
        </p>
        <p className="mt-1 text-xs text-ink-muted">{evidence.note}</p>
      </div>
    </div>
  );
}
