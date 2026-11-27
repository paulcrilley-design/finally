import { amount, cents, expect, open, test, trade } from "./helpers";

test("buying lowers cash, opens a position and updates the portfolio", async ({ page, request }) => {
  await open(page);
  const price = await trade(page, "buy", "AAPL", 5);
  const cash = cents(10_000 - cents(5 * price));

  await expect.poll(() => amount(page, "header-cash")).toBe(cash);
  await expect(page.getByTestId("position-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("position-quantity-AAPL")).toHaveText("5");
  await expect(page.getByTestId("position-row-AAPL").locator("td").nth(1)).toContainText("$");
  await expect(page.getByTestId("heatmap-cell-AAPL")).toBeVisible();

  // The header total tracks cash plus the position at the live price.
  await expect(async () => {
    const [total, now] = await page.evaluate(() => [
      document.querySelector('[data-testid="header-total-value"]')!.textContent!,
      document.querySelector('[data-testid="position-row-AAPL"] td:nth-of-type(3)')!.textContent!,
    ]);
    const number = (text: string) => Number(text.replace(/[^0-9.]/g, ""));
    expect(Math.abs(number(total) - (cash + 5 * number(now)))).toBeLessThan(0.02);
  }).toPass();

  // A second buy adds to the same position.
  const second = await trade(page, "buy", "AAPL", 2);
  await expect(page.getByTestId("position-quantity-AAPL")).toHaveText("7");
  await expect.poll(() => amount(page, "header-cash")).toBe(cents(cash - cents(2 * second)));
  const portfolio = await (await request.get("/api/portfolio")).json();
  expect(portfolio.positions[0].avg_cost).toBeCloseTo((5 * price + 2 * second) / 7, 4);

  // Everything survives a reload.
  await page.reload();
  await expect(page.getByTestId("position-quantity-AAPL")).toHaveText("7");
  await expect.poll(() => amount(page, "header-cash")).toBe(portfolio.cash_balance);
});

test("selling raises cash, then updates and removes the position", async ({ page }) => {
  await open(page);
  await trade(page, "buy", "MSFT", 4);
  const afterBuy = await amount(page, "header-cash");

  const first = await trade(page, "sell", "MSFT", 1.5);
  const afterFirst = cents(afterBuy + cents(1.5 * first));
  await expect.poll(() => amount(page, "header-cash")).toBe(afterFirst);
  await expect(page.getByTestId("position-quantity-MSFT")).toHaveText("2.5");

  const second = await trade(page, "sell", "MSFT", 2.5);
  await expect.poll(() => amount(page, "header-cash")).toBe(cents(afterFirst + cents(2.5 * second)));
  await expect(page.getByTestId("position-row-MSFT")).toHaveCount(0);
  await expect(page.getByTestId("heatmap-cell-MSFT")).toHaveCount(0);
  await expect(page.getByTestId("positions-table")).toContainText("No open positions");
});

test("rejected orders show a reason and change nothing", async ({ page }) => {
  await open(page);
  const message = page.getByTestId("trade-message");
  const attempt = async (side: "buy" | "sell", ticker: string, quantity: string, reason: RegExp) => {
    await page.getByTestId("trade-ticker").fill(ticker);
    await page.getByTestId("trade-quantity").fill(quantity);
    await page.getByTestId(`trade-${side}`).click();
    await expect(message).toHaveText(reason);
    await expect(message).toHaveAttribute("role", "alert");
  };
  await attempt("buy", "AAPL", "100000", /cash/i);
  await attempt("sell", "AAPL", "1", /shares|own|hold/i);
  await attempt("buy", "ZZZZ", "1", /price/i);
  await attempt("buy", "AAPL", "-1", /quantity/i);
  await attempt("buy", "AAPL", "0.00001", /quantity/i);
  await expect(page.getByTestId("header-cash")).toHaveText("$10,000.00");
  await expect(page.getByTestId("positions-table")).toContainText("No open positions");
});
