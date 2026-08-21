// Phase 7 (Conversation Engine): real conversation data, replacing
// src/mock/buyer.ts's canned replies. Same adapter pattern as
// src/api/scenario.ts — snake_case wire format -> camelCase Conversation.

import type { Conversation, ConversationEndReason, ConversationStatus, Sender, TranscriptMessage } from "../types";

interface MessageApi {
  id: string;
  turn_index: number;
  sender: string;
  content: string;
  created_at: string;
}

interface ConversationApi {
  id: string;
  scenario_id: string;
  status: string;
  end_reason: string | null;
  turn_count: number;
  max_turns: number;
  started_at: string;
  completed_at: string | null;
  messages: MessageApi[];
}

function adaptMessage(api: MessageApi): TranscriptMessage {
  return {
    id: api.id,
    turnIndex: api.turn_index,
    sender: api.sender as Sender,
    content: api.content,
  };
}

function adaptConversation(api: ConversationApi): Conversation {
  return {
    id: api.id,
    scenarioId: api.scenario_id,
    status: api.status as ConversationStatus,
    endReason: api.end_reason as ConversationEndReason,
    turnCount: api.turn_count,
    maxTurns: api.max_turns,
    messages: api.messages.map(adaptMessage),
  };
}

async function parseOrThrow(response: Response): Promise<ConversationApi> {
  if (!response.ok) {
    // Never surface raw response bodies (could contain framework detail);
    // a status-coded message is enough for the UI to react to.
    if (response.status === 404) throw new Error("Conversation not found.");
    if (response.status === 409) throw new Error("This conversation has already ended.");
    throw new Error(`Request failed (${response.status})`);
  }
  return (await response.json()) as ConversationApi;
}

export async function startConversation(scenarioId: string): Promise<Conversation> {
  const response = await fetch("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  return adaptConversation(await parseOrThrow(response));
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  const response = await fetch(`/api/conversations/${conversationId}`);
  return adaptConversation(await parseOrThrow(response));
}

export async function sendTurn(conversationId: string, message: string): Promise<Conversation> {
  const response = await fetch(`/api/conversations/${conversationId}/turns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return adaptConversation(await parseOrThrow(response));
}

export async function closeConversation(conversationId: string): Promise<Conversation> {
  const response = await fetch(`/api/conversations/${conversationId}/close`, { method: "POST" });
  return adaptConversation(await parseOrThrow(response));
}
