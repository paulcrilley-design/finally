import { amount, cents, expect, money, open, say, test } from "./helpers";

test("sends a message and shows the reply, with a loading state", async ({ page }) => {
  await open(page);
  await page.route("**/api/chat", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await route.continue();
  });
  await page.getByTestId("chat-input").fill("How is my portfolio?");
  await page.getByTestId("chat-input").press("Enter");
  await expect(page.getByTestId("chat-message-user")).toHaveText("How is my portfolio?");
  await expect(page.getByTestId("chat-loading")).toBeVisible();
  await expect(page.getByTestId("chat-message-assistant")).toContainText(
    "Mock response: your portfolio looks balanced.",
  );
  await expect(page.getByTestId("chat-loading")).toHaveCount(0);
  await expect(page.getByTestId("chat-action")).toHaveCount(0);
});

test("trades appear inline and update the portfolio", async ({ page }) => {
  await open(page);
  await say(page, "buy 5 AAPL");
  const action = page.getByTestId("chat-action");
  await expect(action).toHaveCount(1);
  await expect(action).toHaveAttribute("data-status", "executed");
  await expect(action).toContainText(/Buy 5 AAPL at \$/);
  await expect(page.getByTestId("chat-message-assistant")).toContainText("Mock response: here is your request.");
  await expect(page.getByTestId("position-quantity-AAPL")).toHaveText("5");
  const price = money((await action.innerText()).match(/at (\$[\d,]+\.\d{2})/)![1]);
  const cash = cents(10_000 - cents(5 * price));
  await expect.poll(() => amount(page, "header-cash")).toBe(cash);

  await say(page, "sell 2 AAPL");
  await expect(action.last()).toHaveAttribute("data-status", "executed");
  await expect(action.last()).toContainText("Sell 2 AAPL");
  await expect(page.getByTestId("position-quantity-AAPL")).toHaveText("3");
  await expect.poll(() => amount(page, "header-cash")).toBeGreaterThan(cash);
});

test("changes the watchlist, including a trade in the added ticker", async ({ page }) => {
  await open(page);
  await say(page, "add PYPL and remove NFLX");
  await expect(page.locator('[data-testid="chat-action"][data-status="executed"]')).toHaveCount(2);
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();
  await expect(page.getByTestId("watchlist-row-NFLX")).toHaveCount(0);

  await say(page, "buy 1 PYPL");
  await expect(page.getByTestId("chat-action").last()).toHaveAttribute("data-status", "executed");
  await expect(page.getByTestId("position-quantity-PYPL")).toHaveText("1");
});

test("shows why an action was rejected and changes nothing", async ({ page }) => {
  await open(page);
  const action = page.getByTestId("chat-action");

  await say(page, "buy 100000 AAPL");
  await expect(action.last()).toHaveAttribute("data-status", "rejected");
  await expect(action.last()).toContainText(/cash/i);

  await say(page, "sell 1 TSLA");
  await expect(action.last()).toHaveAttribute("data-status", "rejected");

  await say(page, "please reject: buy 1 AAPL and add PYPL");
  await expect(action).toHaveCount(4);
  await expect(page.locator('[data-testid="chat-action"][data-status="rejected"]')).toHaveCount(4);
  await expect(action.last()).toContainText("Mock reviewer rejection.");

  await expect(page.getByTestId("header-cash")).toHaveText("$10,000.00");
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);
  await expect(page.getByTestId("positions-table")).toContainText("No open positions");
});

test("keeps the conversation after a page reload", async ({ page }) => {
  await open(page);
  await say(page, "buy 1 AAPL");
  await page.reload();
  await expect(page.getByTestId("chat-message-user")).toHaveText("buy 1 AAPL");
  await expect(page.getByTestId("chat-message-assistant")).toContainText("Mock response: here is your request.");
  await expect(page.getByTestId("chat-action")).toHaveAttribute("data-status", "executed");
});
