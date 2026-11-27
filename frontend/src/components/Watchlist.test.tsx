import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WatchlistItem } from "@/lib/types";

import { Watchlist } from "./Watchlist";

function item(ticker: string, price: number | null, change: number | null): WatchlistItem {
  return {
    ticker,
    price,
    previous_price: price,
    timestamp: price === null ? null : 1,
    change: null,
    change_percent: 9.99, // tick to tick: must not be shown
    direction: null,
    prev_close: null,
    day_change: null,
    day_change_percent: change,
  };
}

function cells(ticker: string) {
  const row = screen.getByRole("rowheader", { name: ticker }).closest("tr");
  return within(row as HTMLElement).getAllByRole("cell");
}

describe("Watchlist daily change", () => {
  const rows = [
    item("AAPL", 191.5, 0.79),
    item("MSFT", 418, -0.48),
    item("V", 280, 0),
    item("ZZZZ", null, null),
  ];

  it("shows ticker, price and signed daily change with its tone", () => {
    render(<Watchlist rows={rows} error={null} />);
    expect(screen.getByRole("columnheader", { name: "Day change" })).toBeInTheDocument();
    const expected = [
      ["AAPL", "191.50", "+0.79%", "text-brand-teal-ink"],
      ["MSFT", "418.00", "−0.48%", "text-brand-orange-ink"],
      ["V", "280.00", "0.00%", "text-navy-dark"],
    ];
    for (const [ticker, price, change, tone] of expected) {
      const [priceCell, changeCell] = cells(ticker);
      expect(priceCell).toHaveTextContent(price);
      expect(changeCell).toHaveTextContent(change);
      expect(changeCell).toHaveClass(tone);
    }
  });

  it("shows an em dash for each unknown value", () => {
    render(<Watchlist rows={rows} error={null} />);
    for (const cell of cells("ZZZZ")) expect(cell).toHaveTextContent("—");
  });
});
