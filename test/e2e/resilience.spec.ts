import { startApp, stopApp } from "../app";
import { expect, open, test } from "./helpers";

test("reconnects and resumes streaming after the server restarts", async ({ page }) => {
  await open(page);
  const status = page.getByTestId("connection-status");
  const prices = page.locator('[data-testid^="watchlist-price-"]');

  stopApp();
  await expect(status).toHaveAttribute("data-state", /^(reconnecting|disconnected)$/);
  const stale = (await prices.allInnerTexts()).join();

  await startApp();
  await expect(status).toHaveAttribute("data-state", "connected", { timeout: 20_000 });
  await expect.poll(async () => (await prices.allInnerTexts()).join()).not.toBe(stale);
});

test("shows disconnected when the stream is refused, then recovers", async ({ page }) => {
  await page.route("**/api/stream/prices", (route) => route.fulfill({ status: 503, body: "unavailable" }));
  await page.goto("/");
  const status = page.getByTestId("connection-status");
  await expect(status).toHaveAttribute("data-state", "disconnected");

  await page.unroute("**/api/stream/prices");
  await expect(status).toHaveAttribute("data-state", "connected");
  await expect(page.getByTestId("watchlist-price-AAPL")).toHaveText(/^\$/);
});
