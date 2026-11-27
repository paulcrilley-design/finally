import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TradeBar } from "../src/components/TradeBar";
import { stubFetch } from "./helpers";

function fill(quantity: string) {
  fireEvent.change(screen.getByTestId("trade-quantity"), { target: { value: quantity } });
}

describe("TradeBar", () => {
  it("sends an order for the selected ticker and reports the fill", async () => {
    const trade = { id: "1", ticker: "AAPL", side: "buy", quantity: 2, price: 190, executed_at: "" };
    const fetch = stubFetch({ trade, portfolio: {} });
    const onTraded = vi.fn();
    render(<TradeBar selected="AAPL" onTraded={onTraded} />);
    fill("2");
    fireEvent.click(screen.getByTestId("trade-buy"));
    expect((await screen.findByTestId("trade-message")).textContent).toBe("Bought 2 AAPL at $190.00.");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ ticker: "AAPL", quantity: 2, side: "buy" });
    expect(onTraded).toHaveBeenCalled();
  });

  it("sends a dollar amount in US$ mode and clears the box when the unit changes", async () => {
    const trade = { id: "1", ticker: "AAPL", side: "buy", quantity: 2.631579, price: 190, value: 500, executed_at: "" };
    const fetch = stubFetch({ trade, portfolio: {} });
    render(<TradeBar selected="AAPL" onTraded={vi.fn()} />);
    fill("500");
    fireEvent.click(screen.getByTestId("trade-unit-usd"));
    expect((screen.getByTestId("trade-quantity") as HTMLInputElement).value).toBe("");
    fill("500");
    fireEvent.click(screen.getByTestId("trade-buy"));
    expect((await screen.findByTestId("trade-message")).textContent).toBe(
      "Bought 2.631579 AAPL for $500.00 at $190.00.",
    );
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ ticker: "AAPL", amount: 500, side: "buy" });
  });

  it("shows a rejected order", async () => {
    stubFetch({ error: { code: "insufficient_shares", message: "Not enough shares." } }, 400);
    render(<TradeBar selected="AAPL" onTraded={vi.fn()} />);
    fill("1");
    fireEvent.click(screen.getByTestId("trade-sell"));
    expect((await screen.findByTestId("trade-message")).textContent).toBe("Not enough shares.");
  });

  it("rejects a bad quantity without calling the server", () => {
    const fetch = stubFetch({});
    render(<TradeBar selected="AAPL" onTraded={vi.fn()} />);
    fill("0");
    fireEvent.click(screen.getByTestId("trade-buy"));
    expect(screen.getByTestId("trade-message").textContent).toBe("Enter a quantity above zero.");
    expect(fetch).not.toHaveBeenCalled();
  });
});
