import { useEffect, useRef } from "react";
import { MessageBubble, normalizeMessage } from "./MessageBubble";
import { SubagentCard } from "./SubagentCard";

interface Props {
  messages: unknown[];
  subagents: Record<string, unknown>[];
}

export function ChatPanel({ messages, subagents }: Props) {
  const subagentsById = new Map(subagents.map((subagent) => [String(subagent.id ?? ""), subagent]));
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <section className="chat-panel">
      {messages.length === 0 ? (
        <div className="empty-state">
          <svg className="empty-icon" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="12" y="6" width="40" height="52" rx="3" />
            <line x1="20" y1="16" x2="44" y2="16" />
            <line x1="20" y1="24" x2="40" y2="24" />
            <line x1="20" y1="32" x2="36" y2="32" />
            <line x1="20" y1="40" x2="32" y2="40" />
            <path d="M38 44 l8 8 l-3 3 l-8 -8 z" />
            <line x1="46" y1="52" x2="43" y2="55" />
          </svg>
          <h2>开始论文写作工作流</h2>
          <p>
            输入需求后，writeAgent 将按阶段委派子 Agent 完成学术论文写作，
            并在需要时请求人工确认。
          </p>
        </div>
      ) : (
        messages.map((message, index) => {
          const normalized = normalizeMessage(message);
          const turnSubagents = normalized.toolCalls
            .map((toolCall) => (toolCall.id ? subagentsById.get(toolCall.id) : undefined))
            .filter((item): item is Record<string, unknown> => Boolean(item));
          return (
            <div key={messageKey(message, index)} className="chat-turn">
              <MessageBubble message={message} />
              {turnSubagents.map((subagent, subagentIndex) => (
                <SubagentCard key={String(subagent.id ?? subagentIndex)} subagent={subagent} />
              ))}
            </div>
          );
        })
      )}
      <div ref={bottomRef} />
    </section>
  );
}

function messageKey(message: unknown, index: number): string {
  if (message && typeof message === "object" && "id" in message) {
    return String((message as { id?: unknown }).id ?? index);
  }
  return String(index);
}
