import { describe, expect, it } from "vitest";

import { applyPrices, applyWatchlist, EMPTY_MARKET, nextTick } from "./ticks";
import type { PriceUpdate, WatchlistItem } from "./types";

function quote(ticker: string, price: number, timestamp: number): PriceUpdate {
  return {
    ticker,
    price,
    previous_price: price,
    timestamp,
    change: 0,
    change_percent: 0,
    direction: "flat",
    prev_close: null,
    day_change: null,
    day_change_percent: null,
  };
}

describe("nextTick", () => {
  const first = nextTick(undefined, { price: 100, timestamp: 1 })!;

  it("starts without a direction or flash", () => {
    expect(first).toEqual({ price: 100, timestamp: 1, direction: null, flash: 0 });
  });

  it("ignores a repeated timestamp", () => {
    expect(nextTick(first, { price: 101, timestamp: 1 })).toBe(first);
  });

  it("flashes on each move and keeps direction when the price is unchanged", () => {
    const up = nextTick(first, { price: 100.01, timestamp: 2 })!;
    expect(up).toMatchObject({ direction: "up", flash: 1 });
    const same = nextTick(up, { price: 100.01, timestamp: 3 })!;
    expect(same).toMatchObject({ direction: "up", flash: 1, timestamp: 3 });
    expect(nextTick(same, { price: 100, timestamp: 4 })).toMatchObject({
      direction: "down",
      flash: 2,
    });
  });

  it("ignores a null price or timestamp", () => {
    expect(nextTick(first, { price: null, timestamp: 2 })).toBe(first);
    expect(nextTick(first, { price: 101, timestamp: null })).toBe(first);
    expect(nextTick(undefined, { price: null, timestamp: null })).toBeUndefined();
  });
});

describe("applyPrices and applyWatchlist", () => {
  const items: WatchlistItem[] = [quote("AAPL", 90, 1), quote("MSFT", 400, 1)];

  it("fills only tickers with no streamed quote", () => {
    const streamed = applyPrices(EMPTY_MARKET, { AAPL: quote("AAPL", 100, 2) });
    const data = applyWatchlist(streamed, items);
    expect(data.quotes.AAPL.price).toBe(100);
    expect(data.quotes.MSFT.price).toBe(400);
    expect(data.ticks.MSFT.direction).toBeNull();
  });

  it("keeps tickers absent from the payload and does not mutate its input", () => {
    const before = applyWatchlist(EMPTY_MARKET, items);
    const copy = structuredClone(before);
    const after = applyPrices(before, { AAPL: quote("AAPL", 91, 2) });
    expect(after.quotes.MSFT.price).toBe(400);
    expect(after.ticks.AAPL.direction).toBe("up");
    expect(before).toEqual(copy);
  });
});
