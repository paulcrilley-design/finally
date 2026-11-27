// The scenarios of planning/PLAN.md section 12, plus saved data and narrow screens.
// They share one database and run in order.
import { expect, test } from "@playwright/test";

import { CONTAINER, docker, start, stop } from "./app.mjs";

const DEFAULTS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

test.describe.configure({ mode: "serial" });

const banner = (page) => page.getByRole("banner");
const status = (page) => banner(page).getByRole("status");
const watchlist = (page) => page.getByRole("table", { name: "Watchlist" });
const tickerRow = (page, ticker) =>
  watchlist(page).getByRole("rowheader", { name: ticker, exact: true });
const position = (page, ticker) =>
  page.getByRole("table", { name: "Positions" }).getByRole("row", { name: new RegExp(`^${ticker} `) });

async function cash(page) {
  const text = await banner(page).locator("dt:text-is('Cash') + dd").textContent();
  return Number(text.replace(/[$,]/g, ""));
}

async function open(page) {
  await page.goto("/");
  await expect(status(page)).toHaveText("Connected");
  await expect(watchlist(page)).toBeVisible();
  await expect(banner(page)).not.toContainText("Cash—");
}

async function trade(page, side, ticker, quantity) {
  const form = page.getByRole("form", { name: "Trade" });
  await form.getByLabel("Ticker").fill(ticker);
  await form.getByLabel("Quantity").fill(String(quantity));
  await form.getByRole("button", { name: side }).click();
}

async function say(page, message) {
  const form = page.getByRole("form", { name: "Chat" });
  await form.getByLabel("Message").fill(message);
  await form.getByRole("button", { name: "Send" }).click();
}

async function pricesMove(page) {
  const before = await watchlist(page).innerText();
  await expect.poll(() => watchlist(page).innerText()).not.toBe(before);
}

test("fresh start: default watchlist, $10,000 and streaming prices", async ({ page }) => {
  await open(page);
  await expect(watchlist(page).getByRole("rowheader")).toHaveText(DEFAULTS);
  await expect(banner(page)).toContainText("Total value$10,000.00");
  await expect(banner(page)).toContainText("Cash$10,000.00");
  await expect(page.getByText("No positions yet")).toBeVisible();
  await pricesMove(page);
});

test("add and remove a watchlist ticker", async ({ page }) => {
  await open(page);
  const form = page.getByRole("form", { name: "Add to watchlist" });
  await form.getByLabel("New ticker").fill("pypl");
  await form.getByRole("button", { name: "Add" }).click();
  await expect(tickerRow(page, "PYPL")).toBeVisible();
  await page.getByRole("button", { name: "Remove PYPL" }).click();
  await expect(tickerRow(page, "PYPL")).toHaveCount(0);
});

test("buy shares: cash falls and the position appears", async ({ page }) => {
  await open(page);
  await trade(page, "Buy", "AAPL", 5);
  await expect(page.getByText(/^Bought 5 AAPL at \$/)).toBeVisible();
  await expect(position(page, "AAPL").getByRole("cell").first()).toHaveText("5");
  expect(await cash(page)).toBeLessThan(10_000);
});

test("sell shares: cash rises and the position shrinks, then goes", async ({ page }) => {
  await open(page);
  const before = await cash(page);
  await trade(page, "Sell", "AAPL", 2);
  await expect(position(page, "AAPL").getByRole("cell").first()).toHaveText("3");
  const between = await cash(page);
  expect(between).toBeGreaterThan(before);
  await trade(page, "Sell", "AAPL", 3);
  await expect(page.getByText("No positions yet")).toBeVisible();
  expect(await cash(page)).toBeGreaterThan(between);
});

test("heatmap colours match profit and loss, and the value chart has points", async ({ page }) => {
  await open(page);
  await trade(page, "Buy", "AAPL", 10);
  await expect(position(page, "AAPL")).toBeVisible();
  await trade(page, "Buy", "MSFT", 5);
  await expect(position(page, "MSFT")).toBeVisible();

  const heatmap = page.getByRole("region", { name: "Heatmap" });
  await expect(heatmap.locator("svg rect[fill^='var']")).toHaveCount(2);

  // Read each tile's label and colour in one pass: prices keep moving.
  const tiles = () =>
    heatmap.locator("svg g:has(> rect):has(> text)").evaluateAll((groups) =>
      groups.map((group) => ({
        change: group.querySelector("tspan")?.textContent,
        fill: group.querySelector("rect").getAttribute("fill"),
      })),
    );
  await expect
    .poll(async () => (await tiles()).some(({ change }) => /^[+−]/.test(change)))
    .toBe(true);
  for (const { change, fill } of await tiles()) {
    const tone = change.startsWith("+")
      ? "--brand-teal-ink"
      : change.startsWith("−")
        ? "--brand-orange-ink"
        : "--gray-text";
    expect(fill, change).toBe(`var(${tone})`);
  }

  const chart = page.getByRole("region", { name: "Portfolio value" });
  await expect(chart.getByText(/([2-9]|\d{2,}) points shown/)).toBeVisible();
  await expect(chart.locator("path.recharts-curve")).toHaveAttribute("d", /^M.+L/);
});

test("chat (mocked): the reply and its trade appear inline", async ({ page }) => {
  await open(page);
  const before = await cash(page);
  await say(page, "buy 2 NVDA");
  const log = page.getByRole("log");
  await expect(log.getByText("Here is what you asked for.")).toBeVisible();
  await expect(log.getByText(/Bought 2 NVDA at \$/)).toBeVisible();
  await expect(position(page, "NVDA")).toBeVisible();
  expect(await cash(page)).toBeLessThan(before);
});

test("the price stream reconnects after the server goes away", async ({ page }) => {
  await open(page);
  docker("stop", CONTAINER);
  await expect(status(page)).toHaveText(/Reconnecting|Disconnected/);
  docker("start", CONTAINER);
  await expect(status(page)).toHaveText("Connected", { timeout: 30_000 });
  await pricesMove(page);
});

test("stop and start keep cash, positions, watchlist, trades and chat", async ({ page }) => {
  await open(page);
  await say(page, "add PYPL");
  await expect(tickerRow(page, "PYPL")).toBeVisible();
  const saved = async () => {
    const [portfolio, trades, list, chat] = await Promise.all(
      ["portfolio", "portfolio/history", "watchlist", "chat"].map(async (path) =>
        (await page.request.get(`/api/${path}`)).json(),
      ),
    );
    return {
      cash: portfolio.cash,
      positions: portfolio.positions.map((p) => [p.ticker, p.quantity, p.avg_cost]),
      history: trades.history.slice(0, 3),
      watchlist: list.watchlist.map((item) => item.ticker),
      chat: chat.messages,
    };
  };
  const before = await saved();

  stop();
  stop(); // safe to repeat
  start();
  start();

  await open(page);
  expect(await saved()).toEqual(before);
  await expect(position(page, "NVDA")).toBeVisible();
  await expect(page.getByRole("log").getByText(/Bought 2 NVDA at \$/)).toBeVisible();
});

for (const [name, width, height] of [
  ["phone", 390, 844],
  ["tablet", 768, 1024],
]) {
  test(`${name} width: every panel is usable without horizontal page scroll`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await open(page);
    await expect(position(page, "NVDA")).toBeAttached();
    await page.screenshot({ path: `test-results/${name}.png`, fullPage: true });

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBe(0);

    const controls = page.locator("button:visible, input:visible");
    for (const control of await controls.all()) {
      await control.scrollIntoViewIfNeeded();
      const box = await control.boundingBox();
      expect(box.x, await control.evaluate((el) => el.outerHTML)).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
    }
  });
}
