import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { HeatmapCell } from "../src/components/Heatmap";
import { PnlChart } from "../src/components/PnlChart";
import { PositionsTable } from "../src/components/PositionsTable";
import { SiteHeader } from "../src/components/SiteHeader";

vi.mock("../src/components/Logo", () => ({ Logo: () => null }));
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe() {}
    disconnect() {}
  },
);

describe("portfolio views", () => {
  it("lists positions with signed P&L", () => {
    const position = {
      ticker: "AAPL",
      quantity: 2.5,
      avg_cost: 100,
      current_price: 90,
      market_value: 225,
      unrealized_pnl: -25,
      unrealized_pnl_percent: -10,
      weight: 1,
    };
    render(<PositionsTable positions={[position]} onSelect={vi.fn()} />);
    expect(screen.getByTestId("position-quantity-AAPL").textContent).toBe("2.5");
    expect(screen.getByTestId("position-row-AAPL").textContent).toContain("−$25.00");
  });

  it("marks heatmap cells by P&L", () => {
    render(
      <svg>
        <HeatmapCell name="AAPL" depth={1} width={100} height={80} pnl={5} pnlPercent={1} />
        <HeatmapCell name="TSLA" depth={1} width={100} height={80} pnl={-5} pnlPercent={-1} />
      </svg>,
    );
    expect(screen.getByTestId("heatmap-cell-AAPL").getAttribute("data-pnl")).toBe("profit");
    expect(screen.getByTestId("heatmap-cell-TSLA").getAttribute("data-pnl")).toBe("loss");
  });

  it("exposes the number of history points", () => {
    render(<PnlChart history={[{ total_value: 10000, recorded_at: "2026-11-27T10:00:00+00:00" }]} />);
    expect(screen.getByTestId("pnl-chart").dataset.points).toBe("1");
  });

  it("shows header amounts and connection state", () => {
    render(<SiteHeader totalValue={10000} cash={8100} connection="connected" chatOpen onToggleChat={vi.fn()} />);
    expect(screen.getByTestId("header-total-value").textContent).toBe("$10,000.00");
    expect(screen.getByTestId("header-cash").textContent).toBe("$8,100.00");
    expect(screen.getByTestId("connection-status").dataset.state).toBe("connected");
  });
});
