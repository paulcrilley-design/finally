"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { api, errorMessage } from "../lib/api";
import { formatMoney, formatQuantity } from "../lib/format";
import type { ChatResponse } from "../lib/types";
import { Alert } from "./Card";
import { Button, cn, INPUT, PANEL, Spinner } from "./ui";

type Message = { role: "user"; text: string } | { role: "assistant"; text: string; reply: ChatResponse };

function Action({ status, text, reason }: { status: "executed" | "rejected"; text: string; reason: string | null }) {
  return (
    <li
      data-testid="chat-action"
      data-status={status}
      className={cn(
        "rounded-2xl px-3 py-2 text-xs",
        status === "executed" ? "bg-brand-teal-ink/10 text-brand-teal-ink" : "bg-brand-orange/10 text-brand-orange-ink",
      )}
    >
      <span className="font-semibold">
        {status === "executed" ? "✓ Executed" : "✕ Rejected"}: {text}
      </span>
      {reason && <span className="block">{reason}</span>}
    </li>
  );
}

function Actions({ reply }: { reply: ChatResponse }) {
  if (!reply.trades.length && !reply.watchlist_changes.length) return null;
  return (
    <ul className="mt-2 space-y-2">
      {reply.watchlist_changes.map((change, i) => (
        <Action
          key={`watch-${i}`}
          status={change.status}
          text={`${change.action === "add" ? "Add" : "Remove"} ${change.ticker} ${change.action === "add" ? "to" : "from"} watchlist`}
          reason={change.reason ?? change.review?.reason ?? null}
        />
      ))}
      {reply.trades.map((trade, i) => (
        <Action
          key={`trade-${i}`}
          status={trade.status}
          text={
            `${trade.side === "buy" ? "Buy" : "Sell"} ${formatQuantity(trade.quantity)} ${trade.ticker}` +
            (trade.price == null ? "" : ` at ${formatMoney(trade.price)}`)
          }
          reason={trade.reason ?? trade.review?.reason ?? null}
        />
      ))}
    </ul>
  );
}

/** Docked beside the workstation on wide screens, a drawer below that. Stays mounted when closed. */
export function ChatPanel({
  open,
  onClose,
  onActions,
}: {
  open: boolean;
  onClose: () => void;
  onActions: () => Promise<void> | void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const log = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [messages, loading, open]);

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || loading) return;
    setDraft("");
    setError(null);
    setLoading(true);
    setMessages((all) => [...all, { role: "user", text }]);
    try {
      const reply = await api.chat(text);
      setMessages((all) => [...all, { role: "assistant", text: reply.message, reply }]);
      if (reply.trades.length || reply.watchlist_changes.length) await onActions();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <aside
      data-testid="chat-panel"
      aria-label="AI assistant"
      hidden={!open}
      className={cn(
        PANEL,
        open && "flex",
        "fixed inset-y-3 right-3 z-20 w-[min(360px,calc(100vw-24px))] flex-col p-4",
        "xl:sticky xl:inset-auto xl:top-4 xl:z-auto xl:h-[calc(100vh-101px)] xl:w-auto xl:self-start",
      )}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-display text-base font-semibold">AI assistant</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>
      <div ref={log} className="min-h-0 flex-1 space-y-3 overflow-y-auto" aria-live="polite">
        {messages.length === 0 && (
          <p className="text-xs text-gray-text">
            Ask about your portfolio, or tell me to trade or change your watchlist. For example: “buy 5 AAPL”.
          </p>
        )}
        {messages.map((message, i) =>
          message.role === "user" ? (
            <div key={i} data-testid="chat-message-user" className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl bg-brand-teal-ink px-3 py-2 text-sm break-words whitespace-pre-wrap text-white">
                {message.text}
              </p>
            </div>
          ) : (
            <div key={i} data-testid="chat-message-assistant" className="max-w-[95%]">
              <p
                className={cn(
                  "rounded-2xl px-3 py-2 text-sm break-words whitespace-pre-wrap",
                  message.reply.error ? "bg-brand-orange/10 text-brand-orange-ink" : "bg-surface",
                )}
              >
                {message.text}
              </p>
              <Actions reply={message.reply} />
            </div>
          ),
        )}
        {loading && (
          <div data-testid="chat-loading">
            <Spinner label="Thinking…" />
          </div>
        )}
        {error && <Alert>{error}</Alert>}
      </div>
      <form onSubmit={send} className="mt-3 flex items-end gap-2">
        <textarea
          data-testid="chat-input"
          aria-label="Message the assistant"
          rows={2}
          maxLength={2000}
          placeholder="Ask FinAlly…"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          className={cn(INPUT, "min-w-0 flex-1 resize-none")}
        />
        <Button type="submit" data-testid="chat-send" disabled={loading || !draft.trim()}>
          Send
        </Button>
      </form>
    </aside>
  );
}
