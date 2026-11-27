import { useState, type FormEvent } from "react";

import { formatPrice, formatQuantity } from "@/lib/format";
import type { Side, TradeOrder, TradeResponse } from "@/lib/types";

import { Button, INPUT } from "./ui";

type Result = { ok: boolean; text: string };

/** Market orders. The server decides; its reason is shown when it refuses. */
export function TradeBar({
  onTrade,
}: {
  onTrade: (order: TradeOrder) => Promise<TradeResponse["trade"]>;
}) {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Pressing Enter submits no button: do nothing, never guess a side.
    const button = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const side = button?.value as Side | undefined;
    if (!side || pending) return;
    setPending(true);
    setResult(null);
    try {
      const filled = await onTrade({
        ticker: ticker.trim().toUpperCase(),
        side,
        quantity: Number(quantity.trim() || Number.NaN),
      });
      const verb = filled.side === "buy" ? "Bought" : "Sold";
      setResult({
        ok: true,
        text: `${verb} ${formatQuantity(filled.quantity)} ${filled.ticker} at $${formatPrice(filled.price)}.`,
      });
      setQuantity("");
    } catch (error) {
      setResult({ ok: false, text: (error as Error).message });
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="Trade" noValidate>
      <div className="flex flex-wrap items-end gap-3">
        <label className="w-32 text-sm font-semibold">
          Ticker
          <input
            className={INPUT}
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
            autoCapitalize="characters"
            autoComplete="off"
          />
        </label>
        <label className="w-32 text-sm font-semibold">
          Quantity
          <input
            className={INPUT}
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
            inputMode="decimal"
            autoComplete="off"
          />
        </label>
        <Button type="submit" name="side" value="buy" disabled={pending}>
          Buy
        </Button>
        <Button type="submit" name="side" value="sell" variant="secondary" disabled={pending}>
          Sell
        </Button>
      </div>
      {result && (
        <p
          role={result.ok ? undefined : "alert"}
          aria-live={result.ok ? "polite" : undefined}
          className={`mt-3 text-sm font-semibold ${result.ok ? "text-brand-teal-ink" : "text-brand-orange-ink"}`}
        >
          {result.text}
        </p>
      )}
    </form>
  );
}
