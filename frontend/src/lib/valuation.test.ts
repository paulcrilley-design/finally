import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import type { Position, WatchlistItem } from "./types";
import { valuePortfolio, valuePosition } from "./valuation";

// The same cases the backend tests, so the page and the server agree.
const cases: Position[] = JSON.parse(
  readFileSync(
    path.resolve(process.cwd(), "../backend/tests/fixtures/valuation_cases.json"),
    "utf8",
  ),
);

function position(ticker: string, quantity: number, price: number | null): Position {
  return {
    ticker,
    quantity,
    avg_cost: 100,
    price,
    market_value: null,
    unrealized_pnl: null,
    pnl_percent: null,
  };
}

describe("valuePosition", () => {
  it.each(cases)("matches the server for $quantity at $price", (expected) => {
    expect(valuePosition(expected, expected.price)).toEqual(expected);
  });
});

describe("valuePortfolio", () => {
  const portfolio = {
    cash: 0.1,
    total_value: 0,
    positions: [position("AAPL", 1, 100), position("MSFT", 2, 100)],
  };

  it("uses streamed prices and adds up in cents", () => {
    const quotes = { AAPL: { price: 100.2 } as WatchlistItem };
    expect(valuePortfolio(portfolio, quotes).total_value).toBe(300.3);
  });

  it("has no total while a held price is unknown", () => {
    const unknown = { ...portfolio, positions: [position("ZZZZ", 1, null)] };
    expect(valuePortfolio(unknown, {}).total_value).toBeNull();
  });
});
