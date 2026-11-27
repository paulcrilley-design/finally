import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FLASH_MS, Watchlist } from "../src/components/Watchlist";
import type { WatchlistItem } from "../src/lib/types";
import { price, stubFetch } from "./helpers";

const item: WatchlistItem = {
  ticker: "AAPL",
  price: 190,
  previous_price: 190,
  timestamp: 1,
  direction: "flat",
  prev_close: 190,
  day_change: 0,
  day_change_percent: 0,
};

function setup(prices = {}) {
  const props = { items: [item], history: {}, selected: null, onSelect: vi.fn(), onChanged: vi.fn(), prices };
  const view = render(<Watchlist {...props} />);
  return { ...view, props };
}

describe("Watchlist", () => {
  it("shows the price, flashes on a new tick and clears the flash", () => {
    vi.useFakeTimers();
    const { rerender, props } = setup();
    const cell = screen.getByTestId("watchlist-price-AAPL");
    expect(cell.textContent).toBe("$190.00");

    rerender(<Watchlist {...props} prices={{ AAPL: price("AAPL", 191.25, 2, "up") }} />);
    expect(cell.textContent).toBe("$191.25");
    expect(cell.parentElement!.dataset.flash).toBe("up");
    act(() => vi.advanceTimersByTime(FLASH_MS));
    expect(cell.parentElement!.dataset.flash).toBeUndefined();
  });

  it("selects on row click but not on remove", async () => {
    const fetch = stubFetch(null, 204);
    const { props } = setup();
    fireEvent.click(screen.getByTestId("watchlist-row-AAPL"));
    expect(props.onSelect).toHaveBeenCalledWith("AAPL");
    fireEvent.click(screen.getByTestId("watchlist-remove-AAPL"));
    await waitFor(() => expect(props.onChanged).toHaveBeenCalled());
    expect(props.onSelect).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith("/api/watchlist/AAPL", expect.anything());
  });

  it("adds a ticker, upper-cased", async () => {
    const fetch = stubFetch(item, 201);
    const { props } = setup();
    const input = screen.getByTestId<HTMLInputElement>("watchlist-add-input");
    fireEvent.change(input, { target: { value: "pypl" } });
    fireEvent.click(screen.getByTestId("watchlist-add-button"));
    await waitFor(() => expect(input.value).toBe(""));
    expect(fetch.mock.calls[0][1].body).toBe(JSON.stringify({ ticker: "PYPL" }));
    expect(props.onChanged).toHaveBeenCalled();
  });

  it("shows an add error", async () => {
    stubFetch({ error: { code: "already_watching", message: "Already on the watchlist." } }, 409);
    setup();
    fireEvent.change(screen.getByTestId("watchlist-add-input"), { target: { value: "AAPL" } });
    fireEvent.click(screen.getByTestId("watchlist-add-button"));
    expect((await screen.findByRole("alert")).textContent).toBe("Already on the watchlist.");
  });
});
