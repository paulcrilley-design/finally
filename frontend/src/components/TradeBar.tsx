"use client";

import { useEffect, useState } from "react";
import { api, errorMessage } from "../lib/api";
import { formatMoney, formatQuantity } from "../lib/format";
import type { Side } from "../lib/types";
import { Card } from "./Card";
import { Button, cn, INPUT } from "./ui";

type Unit = "shares" | "usd";

const UNITS: { unit: Unit; label: string }[] = [
  { unit: "shares", label: "Shares" },
  { unit: "usd", label: "US$" },
];

export function TradeBar({ selected, onTraded }: { selected: string | null; onTraded: () => Promise<void> | void }) {
  const [ticker, setTicker] = useState("");
  const [unit, setUnit] = useState<Unit>("shares");
  const [size, setSize] = useState("");
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (selected) setTicker(selected);
    setMessage(null);
  }, [selected]);

  async function trade(side: Side) {
    const symbol = ticker.trim().toUpperCase();
    const value = Number(size);
    if (!symbol) return setMessage({ text: "Enter a ticker.", error: true });
    if (!Number.isFinite(value) || value <= 0) {
      const what = unit === "usd" ? "an amount" : "a quantity";
      return setMessage({ text: `Enter ${what} above zero.`, error: true });
    }
    setBusy(true);
    setMessage(null);
    try {
      const order = unit === "usd" ? { amount: value } : { quantity: value };
      const { trade: done } = await api.trade(symbol, order, side);
      await onTraded();
      const verb = done.side === "buy" ? "Bought" : "Sold";
      const total = unit === "usd" ? ` for ${formatMoney(done.value)}` : "";
      setMessage({
        text: `${verb} ${formatQuantity(done.quantity)} ${done.ticker}${total} at ${formatMoney(done.price)}.`,
        error: false,
      });
    } catch (cause) {
      setMessage({ text: errorMessage(cause), error: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Trade" aside={<p className="text-xs text-gray-text">Market order, instant fill</p>}>
      {/* No default action on Enter: an order is only sent by an explicit Buy or Sell. */}
      <form onSubmit={(event) => event.preventDefault()} className="flex flex-wrap items-end gap-3">
        <label className="min-w-28 flex-1 text-sm font-semibold">
          Ticker
          <input
            data-testid="trade-ticker"
            maxLength={10}
            value={ticker}
            onChange={(event) => setTicker(event.target.value.toUpperCase())}
            className={INPUT}
          />
        </label>
        <div role="group" aria-label="Order size in" className="flex gap-1">
          {UNITS.map((option) => (
            <Button
              key={option.unit}
              data-testid={`trade-unit-${option.unit}`}
              variant={unit === option.unit ? "primary" : "ghost"}
              aria-pressed={unit === option.unit}
              onClick={() => {
                if (unit === option.unit) return;
                setUnit(option.unit);
                setSize(""); // 500 shares must never silently become $500, or the reverse
                setMessage(null);
              }}
            >
              {option.label}
            </Button>
          ))}
        </div>
        <label className="min-w-28 flex-1 text-sm font-semibold">
          {unit === "usd" ? "Amount (US$)" : "Quantity"}
          <input
            data-testid="trade-quantity"
            type="number"
            min="0"
            step={unit === "usd" ? "0.01" : "any"}
            inputMode="decimal"
            value={size}
            onChange={(event) => setSize(event.target.value)}
            className={INPUT}
          />
        </label>
        <Button data-testid="trade-buy" disabled={busy} onClick={() => void trade("buy")}>
          Buy
        </Button>
        <Button variant="danger" data-testid="trade-sell" disabled={busy} onClick={() => void trade("sell")}>
          Sell
        </Button>
      </form>
      {message && (
        <p
          data-testid="trade-message"
          role={message.error ? "alert" : "status"}
          className={cn("mt-2 text-sm font-medium", message.error ? "text-brand-orange-ink" : "text-brand-teal-ink")}
        >
          {message.text}
        </p>
      )}
    </Card>
  );
}
