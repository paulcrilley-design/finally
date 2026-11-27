import { DEFAULT_TICKERS, expect, open, test } from "./helpers";

test("shows the default watchlist, $10k and an empty portfolio", async ({ page, request }) => {
  const health = await (await request.get("/api/health")).json();
  expect(health).toMatchObject({ status: "ok", llm_mock: true, market: { mode: "simulator", tickers: 10 } });

  await open(page);
  await expect(page).toHaveTitle(/FinAlly/);
  await expect(page.getByAltText("openUI")).toBeVisible();
  const rows = page.locator('[data-testid^="watchlist-row-"]');
  await expect(rows).toHaveCount(DEFAULT_TICKERS.length);
  expect(await rows.evaluateAll((all) => all.map((row) => row.getAttribute("data-testid")))).toEqual(
    DEFAULT_TICKERS.map((ticker) => `watchlist-row-${ticker}`),
  );
  for (const ticker of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-price-${ticker}`)).toHaveText(/^\$[\d,]+\.\d{2}$/);
  }
  await expect(page.getByTestId("header-cash")).toHaveText("$10,000.00");
  await expect(page.getByTestId("header-total-value")).toHaveText("$10,000.00");
  await expect(page.getByTestId("positions-table")).toContainText("No open positions");
  await expect(page.locator('[data-testid^="heatmap-cell-"]')).toHaveCount(0);
  await expect(page.getByTestId("chat-panel")).toBeVisible();
});

test("prices stream and the main chart follows the selected ticker", async ({ page }) => {
  await open(page);
  const prices = page.locator('[data-testid^="watchlist-price-"]');
  const first = (await prices.allInnerTexts()).join();
  await expect.poll(async () => (await prices.allInnerTexts()).join()).not.toBe(first);
  // A tick flashes the price, and the sparklines and main chart draw lines from the stream.
  await expect(page.locator("[data-flash]").first()).toBeAttached();
  await expect(page.getByTestId("watchlist").locator("svg").first()).toBeVisible();

  await expect(page.getByTestId("main-chart")).toHaveAttribute("data-ticker", "AAPL");
  await page.getByTestId("watchlist-row-TSLA").click();
  await expect(page.getByTestId("main-chart")).toHaveAttribute("data-ticker", "TSLA");
  await expect(page.getByTestId("trade-ticker")).toHaveValue("TSLA");
  await expect(page.getByTestId("main-chart").locator("svg path").first()).toBeAttached();
});
