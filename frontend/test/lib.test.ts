import { describe, expect, it } from "vitest";
import { api } from "../src/lib/api";
import { formatMoney, formatPercent, formatSignedMoney, pnlState } from "../src/lib/format";
import { valuePortfolio } from "../src/lib/portfolio";
import { applyPrices, EMPTY_PRICES, MAX_POINTS } from "../src/lib/prices";
import type { Portfolio } from "../src/lib/types";
import { price, stubFetch } from "./helpers";

describe("format", () => {
  it("formats money and signed values", () => {
    expect(formatMoney(10000)).toBe("$10,000.00");
    expect(formatMoney(null)).toBe("—");
    expect(formatSignedMoney(12.5)).toBe("+$12.50");
    expect(formatSignedMoney(-3)).toBe("−$3.00");
    expect(formatPercent(-0.001)).toBe("0.00%");
  });

  it("classifies P&L", () => {
    expect([pnlState(1), pnlState(-1), pnlState(0.001), pnlState(null)]).toEqual(["profit", "loss", "flat", "flat"]);
  });
});

describe("applyPrices", () => {
  it("adds a point only when the timestamp changes and drops untracked tickers", () => {
    let state = applyPrices(EMPTY_PRICES, { AAPL: price("AAPL", 1, 1), MSFT: price("MSFT", 2, 1) });
    state = applyPrices(state, { AAPL: price("AAPL", 1, 1) });
    expect(state.history.AAPL).toHaveLength(1);
    expect(state.history.MSFT).toBeUndefined();
    state = applyPrices(state, { AAPL: price("AAPL", 3, 2) });
    expect(state.history.AAPL.map((p) => p.price)).toEqual([1, 3]);
  });

  it("caps the history", () => {
    let state = EMPTY_PRICES;
    for (let i = 0; i < MAX_POINTS + 5; i++) state = applyPrices(state, { A: price("A", i, i) });
    expect(state.history.A).toHaveLength(MAX_POINTS);
  });
});

describe("valuePortfolio", () => {
  const position = {
    ticker: "AAPL",
    quantity: 10,
    avg_cost: 100,
    current_price: 100,
    market_value: 1000,
    unrealized_pnl: 0,
    unrealized_pnl_percent: 0,
    weight: 1,
  };
  const base: Portfolio = { cash_balance: 500, total_value: 1500, positions_value: 1000, unrealized_pnl: 0, positions: [position] };

  it("revalues at live prices", () => {
    const live = valuePortfolio(base, { AAPL: price("AAPL", 110) });
    expect(live.total_value).toBe(1600);
    expect(live.unrealized_pnl).toBe(100);
    expect(live.positions[0].unrealized_pnl_percent).toBe(10);
  });

  it("leaves an unpriced position out of the totals", () => {
    const unpriced = { ...position, current_price: null, market_value: null, unrealized_pnl: null, weight: null };
    const live = valuePortfolio({ ...base, positions: [unpriced] }, {});
    expect(live.total_value).toBe(500);
    expect(live.positions[0].weight).toBeNull();
  });
});

describe("api", () => {
  it("raises the server's error message", async () => {
    stubFetch({ error: { code: "insufficient_cash", message: "Not enough cash." } }, 400);
    await expect(api.trade("AAPL", 1, "buy")).rejects.toMatchObject({ code: "insufficient_cash", message: "Not enough cash." });
  });

  it("handles 204", async () => {
    const fetch = stubFetch(null, 204);
    await expect(api.removeTicker("AAPL")).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledWith("/api/watchlist/AAPL", expect.objectContaining({ method: "DELETE" }));
  });
});
