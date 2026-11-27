import { useEffect, useRef, useState, type FormEvent } from "react";

import { formatPrice, formatQuantity } from "@/lib/format";
import type { ChatAction, ChatMessage } from "@/lib/types";

import { Button, INPUT, Panel, SUBHEADING } from "./ui";

export function describeAction(action: ChatAction): string {
  const done = action.status === "executed";
  if (action.type === "watchlist") {
    if (done) {
      return action.action === "add"
        ? `Added ${action.ticker} to the watchlist`
        : `Removed ${action.ticker} from the watchlist`;
    }
    return `Not done: ${action.action} ${action.ticker}. ${action.reason}`;
  }
  const quantity = formatQuantity(action.quantity);
  if (!done) return `Not done: ${action.side} ${quantity} ${action.ticker}. ${action.reason}`;
  const verb = action.side === "buy" ? "Bought" : "Sold";
  return `${verb} ${quantity} ${action.ticker} at $${formatPrice(action.price ?? null)}`;
}

const BUBBLE = "max-w-[90%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap break-words";
const USER = `${BUBBLE} self-end bg-brand-teal-ink text-white`;
const ASSISTANT = `${BUBBLE} self-start bg-surface text-navy-dark`;

function Message({ message }: { message: ChatMessage }) {
  const mine = message.role === "user";
  return (
    <li className={mine ? USER : ASSISTANT}>
      <span className="sr-only">{mine ? "You: " : "FinAlly: "}</span>
      {message.content}
      {message.actions && message.actions.length > 0 && (
        <ul aria-label="Actions" className="mt-2 space-y-1 font-semibold">
          {message.actions.map((action, index) => (
            <li
              key={index}
              className={
                action.status === "executed" ? "text-brand-teal-ink" : "text-brand-orange-ink"
              }
            >
              <span aria-hidden="true">{action.status === "executed" ? "✓ " : "✕ "}</span>
              {describeAction(action)}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function ChatPanel({
  messages,
  pending,
  error,
  onSend,
}: {
  messages: ChatMessage[];
  pending: string | null;
  error: string;
  onSend: (text: string) => Promise<boolean>;
}) {
  const [open, setOpen] = useState(true);
  const [text, setText] = useState("");
  const log = useRef<HTMLDivElement>(null);

  // Keep the newest message in view.
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [messages, pending, open]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message || pending !== null) return;
    if (await onSend(message)) setText("");
  }

  if (!open) {
    return (
      <Button variant="secondary" aria-expanded={false} onClick={() => setOpen(true)}>
        Open AI chat
      </Button>
    );
  }
  return (
    <Panel className="flex w-full flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 id="chat-heading" className={SUBHEADING}>
          AI copilot
        </h2>
        <Button variant="ghost" size="sm" aria-expanded={true} onClick={() => setOpen(false)}>
          Close chat
        </Button>
      </div>
      <div ref={log} role="log" aria-labelledby="chat-heading" className="max-h-96 overflow-y-auto">
        {messages.length === 0 && pending === null && (
          <p className="text-sm text-gray-text">
            Ask about your portfolio, or say what to buy, sell or watch.
          </p>
        )}
        <ul className="flex flex-col gap-2 pr-2">
          {messages.map((message) => (
            <Message key={message.id} message={message} />
          ))}
          {pending !== null && (
            <>
              <li className={USER}>{pending}</li>
              <li className={ASSISTANT}>Thinking…</li>
            </>
          )}
        </ul>
      </div>
      {error && (
        <p role="alert" className="text-sm font-semibold text-brand-orange-ink">
          {error}
        </p>
      )}
      <form onSubmit={submit} aria-label="Chat" className="flex items-end gap-2">
        <label className="min-w-0 flex-1 text-sm font-semibold">
          Message
          <input
            className={INPUT}
            value={text}
            onChange={(event) => setText(event.target.value)}
            maxLength={1000}
            autoComplete="off"
          />
        </label>
        <Button type="submit" disabled={pending !== null}>
          Send
        </Button>
      </form>
      <p className="text-xs text-gray-text">
        Messages, your portfolio and watched prices are sent to an AI service. The AI can trade this
        simulated account.
      </p>
    </Panel>
  );
}
