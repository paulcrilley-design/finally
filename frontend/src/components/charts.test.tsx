import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { heatmapTiles } from "@/lib/heatmap";
import type { Position } from "@/lib/types";

import { Heatmap } from "./Heatmap";
import { PriceChart } from "./PriceChart";
import { valueDomain } from "./TimeChart";
import { ValueChart } from "./ValueChart";

function position(ticker: string, value: number | null, percent: number | null): Position {
  return {
    ticker,
    quantity: 1,
    avg_cost: 100,
    price: value,
    market_value: value,
    unrealized_pnl: null,
    pnl_percent: percent,
  };
}

const positions = [
  position("MSFT", 100, -2),
  position("AAPL", 300, 1.5),
  position("V", 50, 0),
  position("ZZZZ", null, null),
];

describe("heatmapTiles", () => {
  it("sizes by value, signs the change and leaves out unknown prices", () => {
    expect(heatmapTiles(positions)).toEqual([
      { name: "MSFT", size: 100, change: "−2.00%", tone: "loss" },
      { name: "AAPL", size: 300, change: "+1.50%", tone: "gain" },
      { name: "V", size: 50, change: "0.00%", tone: "flat" },
    ]);
  });
});

describe("Heatmap", () => {
  it("lists the positions largest first for screen readers", () => {
    render(<Heatmap tiles={heatmapTiles(positions)} />);
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "AAPL +1.50%",
      "MSFT −2.00%",
      "V 0.00%",
    ]);
  });

  it("says when there is nothing to show", () => {
    render(<Heatmap tiles={[]} />);
    expect(screen.getByText("No positions to show")).toBeInTheDocument();
  });
});

describe("PriceChart", () => {
  it("waits for prices, then summarises them in words", () => {
    const { rerender, container } = render(<PriceChart ticker="AAPL" points={[]} />);
    expect(screen.getByText("Waiting for AAPL prices")).toBeInTheDocument();
    rerender(
      <PriceChart
        ticker="AAPL"
        points={[
          { time: 1, price: 101 },
          { time: 2, price: 99 },
        ]}
      />,
    );
    expect(container).toHaveTextContent("Latest $99.00, low $99.00, high $101.00");
  });
});

describe("ValueChart", () => {
  it("covers loading, failure, empty and recorded states", () => {
    const { rerender, container } = render(<ValueChart history={null} failed={false} />);
    expect(container).toHaveTextContent("Loading value history");
    rerender(<ValueChart history={null} failed />);
    expect(container).toHaveTextContent("Value history unavailable");
    rerender(<ValueChart history={[]} failed={false} />);
    expect(container).toHaveTextContent("No value history yet");
    const point = { recorded_at: "2026-01-01T10:00:00.000000+00:00", total_value: 10000 };
    rerender(<ValueChart history={[point]} failed={false} />);
    expect(container).toHaveTextContent("Latest recorded value $10,000.00, 1 point shown.");
  });
});

describe("valueDomain", () => {
  it("widens a nearly flat series and leaves others to the chart", () => {
    expect(valueDomain([189.97, 189.99])).toEqual([189.95, 190.01]);
    expect(valueDomain([100, 101])).toEqual(["auto", "auto"]);
  });
});
