import { useEffect, useRef, useState } from "react";
import type { Scenario, TranscriptMessage } from "../types";
import { getMockBuyerReply, resetMockBuyer } from "../mock/buyer";

interface Props {
  scenario: Scenario;
  onComplete: (transcript: TranscriptMessage[]) => void;
}

function idFor(turnIndex: number, sender: string) {
  return `${sender}-${turnIndex}`;
}

export function Conversation({ scenario, onComplete }: Props) {
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    resetMockBuyer();
    setTranscript([
      { id: idFor(1, "buyer"), turnIndex: 1, sender: "buyer", content: getMockBuyerReply() },
    ]);
  }, [scenario.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const turnsUsed = transcript.filter((m) => m.sender === "rep").length;
  const atTurnLimit = turnsUsed >= scenario.maxTurns;

  function sendMessage() {
    const trimmed = draft.trim();
    if (!trimmed || atTurnLimit) return;

    const repTurn: TranscriptMessage = {
      id: idFor(transcript.length + 1, "rep"),
      turnIndex: transcript.length + 1,
      sender: "rep",
      content: trimmed,
    };
    const buyerTurn: TranscriptMessage = {
      id: idFor(transcript.length + 2, "buyer"),
      turnIndex: transcript.length + 2,
      sender: "buyer",
      content: getMockBuyerReply(),
    };

    setTranscript((prev) => [...prev, repTurn, buyerTurn]);
    setDraft("");
  }

  return (
    <main className="flex min-h-screen flex-col bg-bg text-ink">
      <header className="border-b border-line px-6 py-4">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-amber">Live Roleplay</p>
            <h1 className="font-display text-lg font-semibold">{scenario.title}</h1>
          </div>
          <p className="font-mono text-xs text-ink-muted">
            Turn {turnsUsed}/{scenario.maxTurns}
          </p>
        </div>
      </header>

      <div className="mx-auto w-full max-w-2xl flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {transcript.map((m) => (
          <div key={m.id} className={`flex ${m.sender === "rep" ? "justify-end" : "justify-start"}`}>
            <div className="max-w-md">
              <p
                className={`font-mono text-[11px] uppercase tracking-wider ${
                  m.sender === "rep" ? "text-right text-rep" : "text-ink-muted"
                }`}
              >
                {m.sender === "rep" ? "You" : scenario.buyerPersona.name}
              </p>
              <div
                className={`mt-1 rounded-lg border px-4 py-2 text-sm leading-relaxed ${
                  m.sender === "rep"
                    ? "border-rep/40 bg-panel text-ink"
                    : "border-line bg-surface text-ink"
                }`}
              >
                {m.content}
              </div>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <footer className="border-t border-line px-6 py-4">
        <div className="mx-auto flex max-w-2xl gap-2">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
            disabled={atTurnLimit}
            placeholder={atTurnLimit ? "Turn limit reached" : "Type your response…"}
            className="flex-1 rounded-md border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-amber focus:outline-none disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={atTurnLimit || !draft.trim()}
            className="rounded-md bg-rep px-4 py-2 text-sm font-medium text-bg disabled:opacity-40"
          >
            Send
          </button>
        </div>
        <div className="mx-auto mt-3 max-w-2xl">
          <button
            onClick={() => onComplete(transcript)}
            className="text-xs text-ink-muted underline decoration-line underline-offset-4 hover:text-ink"
          >
            End conversation and see evaluation →
          </button>
        </div>
      </footer>
    </main>
  );
}
