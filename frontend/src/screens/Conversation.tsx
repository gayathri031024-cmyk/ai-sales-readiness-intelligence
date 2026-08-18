import { useEffect, useRef, useState } from "react";
import type { Conversation as ConversationRecord, Scenario } from "../types";
import { closeConversation, sendTurn, startConversation } from "../api/conversation";

interface Props {
  scenario: Scenario;
  onComplete: (conversationId: string) => void;
}

/**
 * Phase 7 (Conversation Engine): this screen now drives the real
 * multi-turn conversation API (src/api/conversation.ts) instead of
 * src/mock/buyer.ts's canned replies. The backend conversation record is
 * the single source of truth — this component always replaces its local
 * `conversation` state from the API response rather than growing its own
 * parallel transcript, per ARCHITECTURE.md §2's "fetched, not duplicated
 * client-side" state-management rule.
 *
 * The rep always speaks first (see backend DECISIONS.md) — there is no
 * scripted opening buyer line here anymore.
 */
export function Conversation({ scenario, onComplete }: Props) {
  const [conversation, setConversation] = useState<ConversationRecord | null>(null);
  const [initError, setInitError] = useState<string | null>(null);
  const [turnError, setTurnError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setConversation(null);
    setInitError(null);
    startConversation(scenario.id)
      .then((c) => {
        if (!cancelled) setConversation(c);
      })
      .catch((err: Error) => {
        if (!cancelled) setInitError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [scenario.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages.length]);

  const isTerminal = conversation?.status === "completed";

  async function sendMessage() {
    const trimmed = draft.trim();
    if (!trimmed || !conversation || isTerminal || sending) return;

    setSending(true);
    setTurnError(null);
    try {
      const updated = await sendTurn(conversation.id, trimmed);
      setConversation(updated);
      setDraft("");
    } catch (err) {
      setTurnError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  async function endConversation() {
    if (!conversation) return;
    try {
      const updated = isTerminal ? conversation : await closeConversation(conversation.id);
      onComplete(updated.id);
    } catch (err) {
      setTurnError((err as Error).message);
    }
  }

  if (initError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg px-4 text-ink">
        <div className="max-w-md text-center">
          <p className="font-mono text-xs uppercase tracking-widest text-amber">Couldn't start conversation</p>
          <p className="mt-3 text-sm text-ink-muted">{initError}</p>
        </div>
      </main>
    );
  }

  if (!conversation) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg text-ink-faint">
        <p className="font-mono text-xs uppercase tracking-widest">Starting conversation…</p>
      </main>
    );
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
            Turn {conversation.turnCount}/{conversation.maxTurns}
          </p>
        </div>
      </header>

      <div className="mx-auto w-full max-w-2xl flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {conversation.messages.length === 0 && (
          <p className="text-center text-xs text-ink-faint">
            Open with your first message — the conversation starts with you.
          </p>
        )}
        {conversation.messages.map((m) => (
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
        {sending && (
          <p className="text-center font-mono text-[11px] uppercase tracking-wider text-ink-faint">
            {scenario.buyerPersona.name} is responding…
          </p>
        )}
        <div ref={bottomRef} />
      </div>

      <footer className="border-t border-line px-6 py-4">
        <div className="mx-auto max-w-2xl">
          {isTerminal && (
            <p className="mb-3 rounded-md border border-amber/40 bg-amber/10 px-4 py-2 text-xs text-amber">
              Scenario ended
              {conversation.endReason === "turn_limit" && " — turn limit reached."}
              {conversation.endReason === "patience_exhausted" && " — the buyer ran out of patience."}
              {conversation.endReason === "explicit_close" && " — you ended the conversation."}
            </p>
          )}
          {turnError && <p className="mb-3 text-xs text-amber">{turnError}</p>}
          <div className="flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendMessage();
              }}
              disabled={isTerminal || sending}
              placeholder={isTerminal ? "Scenario ended" : "Type your response…"}
              className="flex-1 rounded-md border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-amber focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={isTerminal || sending || !draft.trim()}
              className="rounded-md bg-rep px-4 py-2 text-sm font-medium text-bg disabled:opacity-40"
            >
              {sending ? "Sending…" : "Send"}
            </button>
          </div>
        </div>
        <div className="mx-auto mt-3 max-w-2xl">
          <button
            onClick={endConversation}
            className="text-xs text-ink-muted underline decoration-line underline-offset-4 hover:text-ink"
          >
            End conversation and see evaluation →
          </button>
        </div>
      </footer>
    </main>
  );
}
