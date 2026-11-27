// Prices seen since the page loaded, per ticker. Pure.

import type { PriceMap } from "./types";

export const MAX_POINTS = 1800; // about 15 minutes at two updates a second

export type PricePoint = { time: number; price: number }; // time in Unix seconds

export type History = Record<string, PricePoint[]>;

export function appendHistory(history: History, prices: PriceMap): History {
  const next = { ...history };
  for (const [ticker, { price, timestamp }] of Object.entries(prices)) {
    const points = next[ticker] ?? [];
    if (price == null || timestamp == null || points.at(-1)?.time === timestamp) continue;
    next[ticker] = [...points.slice(-(MAX_POINTS - 1)), { time: timestamp, price }];
  }
  return next;
}
