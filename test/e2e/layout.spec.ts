import { expect, open, say, test } from "./helpers";

for (const width of [375, 768, 1024, 1280, 1440]) {
  test(`fits ${width}px without horizontal scrolling and keeps the chat usable`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await open(page);
    const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(await overflow()).toBeLessThanOrEqual(0);

    const panel = page.getByTestId("chat-panel");
    if (width >= 1280) {
      await expect(panel).toBeVisible();
    } else {
      await expect(panel).toBeHidden();
      await page.getByTestId("chat-toggle").click();
      await expect(panel).toBeVisible();
    }
    await say(page, "buy 1 AAPL");
    await expect(page.getByTestId("chat-action")).toHaveAttribute("data-status", "executed");
    expect(await overflow()).toBeLessThanOrEqual(0);
    await panel.getByRole("button", { name: "Close" }).click();
    await expect(panel).toBeHidden();
    await expect(page.getByTestId("position-row-AAPL")).toBeVisible();
  });
}

test("controls use the openUI type scale", async ({ page }) => {
  await open(page);
  // planning/OUI_FORMAT.md: buttons are 14px semibold, input text is 14px.
  for (const id of ["trade-buy", "trade-sell", "watchlist-add-button", "chat-toggle", "chat-send"]) {
    await expect(page.getByTestId(id), id).toHaveCSS("font-size", "14px");
    await expect(page.getByTestId(id), id).toHaveCSS("font-weight", "600");
  }
  for (const id of ["trade-ticker", "watchlist-add-input", "chat-input"]) {
    await expect(page.getByTestId(id), id).toHaveCSS("font-size", "14px");
  }
});
