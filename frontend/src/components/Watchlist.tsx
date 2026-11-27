"use client";

import { useEffect, useState, type FormEvent } from "react";
import { api, errorMessage } from "../lib/api";
import { formatMoney, formatPercent, PNL_TEXT, pnlState } from "../lib/format";
import type { PricePoint } from "../lib/prices";
import type { Direction, PriceMap, WatchlistItem } from "../lib/types";
import { Card, Empty } from "./Card";
import { Sparkline } from "./Sparkline";
import { Button, cn, INPUT } from "./ui";

export const FLASH_MS = 150;

/** The tick direction for FLASH_MS after each new timestamp, otherwise null. The tint then fades out. */
function useFlash(timestamp: number | undefined, direction: Direction | undefined) {
  const [flash, setFlash] = useState<Direction | null>(null);
  useEffect(() => {
    if (timestamp === undefined || !direction || direction === "flat") return setFlash(null);
    setFlash(direction);
    const timer = setTimeout(() => setFlash(null), FLASH_MS);
    return () => clearTimeout(timer);
  }, [timestamp, direction]);
  return flash;
}

function Row({
  item,
  live,
  points,
  selected,
  onSelect,
  onRemove,
}: {
  item: WatchlistItem;
  live: PriceMap[string] | undefined;
  points: PricePoint[];
  selected: boolean;
  onSelect: () => void;
  onRemove: () => void;
}) {
  const { ticker } = item;
  const price = live?.price ?? item.price;
  const direction = live?.direction ?? item.direction;
  const dayChange = live ? live.day_change_percent : item.day_change_percent;
  const flash = useFlash(live?.timestamp, live?.direction);

  return (
    <tr
      data-testid={`watchlist-row-${ticker}`}
      onClick={onSelect}
      className={cn("cursor-pointer border-t border-stroke hover:bg-surface", selected && "bg-surface")}
    >
      <th scope="row" className={cn("border-l-2 py-1 pl-2 text-left", selected ? "border-brand-orange" : "border-transparent")}>
        {/* The click bubbles to the row; the button makes the row keyboard accessible. */}
        <button
          type="button"
          aria-pressed={selected}
          className="rounded font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-teal"
        >
          {ticker}
        </button>
      </th>
      <td className="py-1">
        <Sparkline points={points} />
      </td>
      <td className="py-1 text-right whitespace-nowrap tabular-nums">
        <span
          data-flash={flash ?? undefined}
          className={cn(
            "inline-flex items-center gap-1 rounded-md px-1 py-0.5",
            // The tint appears at once and fades over 500ms when removed.
            !flash && "transition-colors duration-500",
            flash === "up" && "bg-brand-teal-ink/15",
            flash === "down" && "bg-brand-orange/25",
          )}
        >
          <span
            className={cn("w-3 text-[10px]", direction === "down" ? "text-brand-orange-ink" : "text-brand-teal-ink")}
            aria-label={direction === "up" ? "up" : direction === "down" ? "down" : undefined}
          >
            {direction === "up" ? "▲" : direction === "down" ? "▼" : ""}
          </span>
          <span data-testid={`watchlist-price-${ticker}`}>{formatMoney(price)}</span>
        </span>
      </td>
      <td className={cn("py-1 text-right text-xs whitespace-nowrap tabular-nums", PNL_TEXT[pnlState(dayChange)])}>
        {formatPercent(dayChange)}
      </td>
      <td className="py-1 text-right">
        <button
          type="button"
          data-testid={`watchlist-remove-${ticker}`}
          aria-label={`Remove ${ticker}`}
          title={`Remove ${ticker}`}
          onClick={(event) => {
            event.stopPropagation();
            onRemove();
          }}
          className="size-6 rounded-full text-brand-orange-ink hover:bg-brand-orange/10 focus-visible:outline-2 focus-visible:outline-brand-teal"
        >
          ×
        </button>
      </td>
    </tr>
  );
}

export function Watchlist({
  items,
  prices,
  history,
  selected,
  onSelect,
  onChanged,
}: {
  items: WatchlistItem[] | null;
  prices: PriceMap;
  history: Record<string, PricePoint[]>;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onChanged: () => Promise<void> | void;
}) {
  const [ticker, setTicker] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function change(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      await onChanged();
      return true;
    } catch (cause) {
      setError(errorMessage(cause));
      return false;
    }
  }

  async function add(event: FormEvent) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (!symbol || busy) return;
    setBusy(true);
    if (await change(() => api.addTicker(symbol))) setTicker("");
    setBusy(false);
  }

  return (
    <Card title="Watchlist" data-testid="watchlist">
      {items?.length ? (
        <table className="w-full text-sm">
          <thead className="text-xs text-gray-text">
            <tr>
              <th scope="col" className="pb-1 pl-2 text-left font-medium">Ticker</th>
              <th scope="col" className="pb-1 text-left font-medium">Trend</th>
              <th scope="col" className="pb-1 text-right font-medium">Price</th>
              <th scope="col" className="pb-1 text-right font-medium">Day</th>
              <th scope="col">
                <span className="sr-only">Remove</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <Row
                key={item.ticker}
                item={item}
                live={prices[item.ticker]}
                points={history[item.ticker] ?? []}
                selected={item.ticker === selected}
                onSelect={() => onSelect(item.ticker)}
                onRemove={() => void change(() => api.removeTicker(item.ticker))}
              />
            ))}
          </tbody>
        </table>
      ) : (
        <Empty>{items ? "Your watchlist is empty. Add a ticker below." : "Loading watchlist…"}</Empty>
      )}
      <form onSubmit={add} className="mt-3 flex items-end gap-2">
        <input
          data-testid="watchlist-add-input"
          aria-label="Ticker to add"
          aria-invalid={Boolean(error)}
          placeholder="Add ticker, e.g. PYPL"
          maxLength={10}
          value={ticker}
          onChange={(event) => setTicker(event.target.value.toUpperCase())}
          className={cn(INPUT, "min-w-0 flex-1")}
        />
        <Button type="submit" variant="secondary" data-testid="watchlist-add-button" disabled={busy}>
          Add
        </Button>
      </form>
      {error && (
        <p role="alert" className="mt-2 text-sm text-brand-orange-ink">
          {error}
        </p>
      )}
    </Card>
  );
}
