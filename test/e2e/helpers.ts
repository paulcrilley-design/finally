import { expect, test as base, type Page } from "@playwright/test";
import { freshApp } from "../app";

export const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

/** Every test starts from a freshly seeded database and fails on any uncaught error in the page. */
export const test = base.extend<{ fresh: void }>({
  fresh: [
    async ({}, use) => {
      await freshApp();
      await use();
    },
    { auto: true },
  ],
  page: async ({ page }, use) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await use(page);
    expect(errors, "uncaught page errors").toEqual([]);
  },
});

export { expect };

/** `$10,000.00` -> 10000 */
export const money = (text: string) => Number(text.replace(/[^0-9.]/g, ""));

export async function amount(page: Page, testId: string): Promise<number> {
  return money(await page.getByTestId(testId).innerText());
}

export async function open(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-state", "connected");
  await expect(page.getByTestId("header-cash")).toContainText("$");
  await expect(page.getByTestId("watchlist-price-AAPL")).toContainText("$");
}

/** Places a trade with the trade bar and returns the fill price from the success message. */
export async function trade(page: Page, side: "buy" | "sell", ticker: string, quantity: number): Promise<number> {
  await page.getByTestId("trade-ticker").fill(ticker);
  await page.getByTestId("trade-quantity").fill(String(quantity));
  await page.getByTestId(`trade-${side}`).click();
  const verb = side === "buy" ? "Bought" : "Sold";
  const message = page.getByTestId("trade-message");
  await expect(message).toHaveText(new RegExp(`^${verb} ${quantity} ${ticker} at \\$[\\d,]+\\.\\d{2}\\.$`));
  return money((await message.innerText()).split(" at ")[1].replace(/\.$/, ""));
}

export async function say(page: Page, text: string): Promise<void> {
  const replies = page.getByTestId("chat-message-assistant");
  const before = await replies.count();
  await page.getByTestId("chat-input").fill(text);
  await page.getByTestId("chat-send").click();
  await expect(replies).toHaveCount(before + 1);
}

export const cents = (value: number) => Math.round(value * 100) / 100;
