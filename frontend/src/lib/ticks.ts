// Price movement rules. Pure, so React may call them twice.

import type { PriceMap, WatchlistItem } from "./types";

export type Tick = {
  price: number; // the last price this client showed
  timestamp: number;
  direction: "up" | "down" | null;
  flash: number; // counts moves, so each one restarts the animation
};

type Quoted = Pick<WatchlistItem, "price" | "timestamp">;

export function nextTick(prev: Tick | undefined, update: Quoted): Tick | undefined {
  const { price, timestamp } = update;
  if (price == null || timestamp == null) return prev;
  if (!prev) return { price, timestamp, direction: null, flash: 0 };
  if (timestamp === prev.timestamp) return prev; // repeated event
  if (price === prev.price) return { ...prev, timestamp };
  // Compared with what was shown, not the server's direction: the client can miss ticks.
  const direction = price > prev.price ? "up" : "down";
  return { price, timestamp, direction, flash: prev.flash + 1 };
}

export type MarketData = {
  quotes: Record<string, WatchlistItem>;
  ticks: Record<string, Tick>;
};

export const EMPTY_MARKET: MarketData = { quotes: {}, ticks: {} };

function applyQuotes(data: MarketData, updates: WatchlistItem[]): MarketData {
  const quotes = { ...data.quotes };
  const ticks = { ...data.ticks };
  for (const update of updates) {
    quotes[update.ticker] = update;
    const tick = nextTick(ticks[update.ticker], update);
    if (tick) ticks[update.ticker] = tick;
  }
  return { quotes, ticks };
}

// Tickers absent from a payload keep their last values.
export function applyPrices(data: MarketData, prices: PriceMap): MarketData {
  const updates = Object.entries(prices).map(([ticker, price]) => ({ ...price, ticker }));
  return applyQuotes(data, updates);
}

// The watchlist response never overwrites a quote already held.
export function applyWatchlist(data: MarketData, items: WatchlistItem[]): MarketData {
  const missing = items.filter((item) => item.price != null && !data.quotes[item.ticker]);
  return applyQuotes(data, missing);
}
