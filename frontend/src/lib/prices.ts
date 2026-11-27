import type { PriceMap } from "./types";

export interface PricePoint {
  time: number; // milliseconds
  price: number;
}

export interface PriceState {
  latest: PriceMap;
  /** Points per ticker since page load, for the sparklines and main chart. */
  history: Record<string, PricePoint[]>;
}

export const MAX_POINTS = 600;
export const EMPTY_PRICES: PriceState = { latest: {}, history: {} };

/**
 * Applies one SSE event. The event lists every tracked ticker, so anything
 * missing is dropped. A point is added only when a ticker's timestamp changes.
 */
export function applyPrices(state: PriceState, event: PriceMap): PriceState {
  const history: PriceState["history"] = {};
  for (const [ticker, update] of Object.entries(event)) {
    const points = state.history[ticker] ?? [];
    history[ticker] =
      state.latest[ticker]?.timestamp === update.timestamp
        ? points
        : [...points, { time: update.timestamp * 1000, price: update.price }].slice(-MAX_POINTS);
  }
  return { latest: event, history };
}
