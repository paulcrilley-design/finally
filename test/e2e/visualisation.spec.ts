import { expect, open, test, trade } from "./helpers";

test("the heatmap has one cell per position and the P&L chart gains points", async ({ page }) => {
  await open(page);
  const chart = page.getByTestId("pnl-chart");
  const points = async () => Number(await chart.getAttribute("data-points"));
  await expect.poll(points).toBeGreaterThanOrEqual(1);
  const before = await points();

  await trade(page, "buy", "AAPL", 10);
  await trade(page, "buy", "TSLA", 5);
  await expect.poll(points).toBeGreaterThanOrEqual(before + 2);
  // A flat line has no height, so check the path data instead of visibility.
  await expect(chart.locator("path.recharts-curve")).toHaveAttribute("d", /^M[\d.]+,[\d.]+[LC]/);

  for (const ticker of ["AAPL", "TSLA"]) {
    const cell = page.getByTestId(`heatmap-cell-${ticker}`);
    await expect(cell).toBeVisible();
    await expect(cell).toHaveAttribute("data-pnl", /^(profit|loss|flat)$/);
    await expect(cell).toContainText(ticker);
    await expect(cell).toContainText("%");
  }
});

test("the P&L chart picks up periodic snapshots without any trade", async ({ page }) => {
  test.setTimeout(100_000);
  await open(page);
  const chart = page.getByTestId("pnl-chart");
  // Snapshots are taken every 30 s and the page refreshes the history every 30 s.
  await expect.poll(async () => Number(await chart.getAttribute("data-points")), { timeout: 75_000 }).toBeGreaterThanOrEqual(2);
});

test("heatmap colours follow profit and loss", async ({ page }) => {
  // Fixed positions and no price stream, so the colour of each cell is known.
  const position = (ticker: string, pnl: number) => ({
    ticker, quantity: 10, avg_cost: 100, current_price: 100 + pnl / 10, market_value: 1000 + pnl,
    unrealized_pnl: pnl, unrealized_pnl_percent: pnl / 10, weight: 1 / 3,
  });
  await page.route("**/api/stream/prices", (route) => route.abort());
  await page.route("**/api/portfolio", (route) =>
    route.fulfill({
      json: {
        cash_balance: 7000, total_value: 10_000, positions_value: 3000, unrealized_pnl: 0,
        positions: [position("AAPL", 100), position("TSLA", -100), position("MSFT", 0)],
      },
    }),
  );
  await page.goto("/");

  // Brand tokens from planning/OUI_FORMAT.md.
  const expected = [
    ["AAPL", "profit", "rgb(49, 95, 98)", "+10.00%"],
    ["TSLA", "loss", "rgb(143, 74, 27)", "−10.00%"],
    ["MSFT", "flat", "rgb(102, 102, 102)", "0.00%"],
  ];
  for (const [ticker, state, colour, label] of expected) {
    const cell = page.getByTestId(`heatmap-cell-${ticker}`);
    await expect(cell).toHaveAttribute("data-pnl", state);
    await expect(cell.locator("rect")).toHaveCSS("fill", colour);
    await expect(cell).toContainText(label);
  }
});
