import { expect, open, test } from "./helpers";

test("adds and removes a ticker, and the change persists", async ({ page }) => {
  await open(page);
  await page.getByTestId("watchlist-add-input").fill("pypl");
  await page.getByTestId("watchlist-add-button").click();
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();
  await expect(page.getByTestId("watchlist-price-PYPL")).toHaveText(/^\$[\d,]+\.\d{2}$/);
  await expect(page.getByTestId("watchlist-add-input")).toHaveValue("");

  await page.reload();
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();

  await page.getByTestId("watchlist-remove-PYPL").click();
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);
  await page.getByTestId("watchlist-remove-NFLX").click();
  await expect(page.getByTestId("watchlist-row-NFLX")).toHaveCount(0);

  await page.reload();
  await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();
  await expect(page.locator('[data-testid^="watchlist-row-"]')).toHaveCount(9);
});

test("explains why a ticker cannot be added", async ({ page }) => {
  await open(page);
  const alert = page.getByTestId("watchlist").getByRole("alert");
  for (const bad of ["AAPL", "123!!"]) {
    await page.getByTestId("watchlist-add-input").fill(bad);
    await page.getByTestId("watchlist-add-button").click();
    await expect(alert).toHaveText(/\w+ \w+/);
    await expect(page.locator('[data-testid^="watchlist-row-"]')).toHaveCount(10);
  }
});

test("a held ticker keeps streaming after it leaves the watchlist", async ({ page, request }) => {
  const bought = await request.post("/api/portfolio/trade", { data: { ticker: "NFLX", quantity: 1, side: "buy" } });
  expect(bought.ok()).toBeTruthy();
  await open(page);
  await page.getByTestId("watchlist-remove-NFLX").click();
  await expect(page.getByTestId("watchlist-row-NFLX")).toHaveCount(0);
  const row = page.getByTestId("position-row-NFLX");
  const price = row.locator("td").nth(2);
  await expect(price).toHaveText(/^\$/);
  const first = await price.innerText();
  await expect.poll(() => price.innerText(), { timeout: 20_000 }).not.toBe(first);
});
