import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatPanel } from "../src/components/ChatPanel";
import { stubFetch } from "./helpers";

function send(text: string) {
  fireEvent.change(screen.getByTestId("chat-input"), { target: { value: text } });
  fireEvent.click(screen.getByTestId("chat-send"));
}

describe("ChatPanel", () => {
  it("shows loading, the reply and each action, then refreshes", async () => {
    stubFetch({
      message: "Done.",
      trades: [{ ticker: "AAPL", side: "buy", quantity: 5, status: "executed", price: 191.25, reason: null, review: null }],
      watchlist_changes: [{ ticker: "PYPL", action: "add", status: "rejected", reason: "Already on the watchlist.", review: null }],
      error: null,
    });
    const onActions = vi.fn();
    render(<ChatPanel open onClose={vi.fn()} onActions={onActions} />);
    send("buy 5 AAPL");
    expect(screen.getByTestId("chat-loading")).toBeTruthy();
    expect(screen.getByTestId("chat-message-user").textContent).toBe("buy 5 AAPL");
    expect((await screen.findByTestId("chat-message-assistant")).textContent).toContain("Done.");
    expect(screen.getAllByTestId("chat-action").map((a) => a.dataset.status)).toEqual(["rejected", "executed"]);
    expect(screen.queryByTestId("chat-loading")).toBeNull();
    expect(onActions).toHaveBeenCalled();
  });

  it("shows a request failure as an alert", async () => {
    stubFetch({ error: { code: "invalid_request", message: "Message is too long." } }, 422);
    render(<ChatPanel open onClose={vi.fn()} onActions={vi.fn()} />);
    send("hello");
    expect((await screen.findByRole("alert")).textContent).toBe("Message is too long.");
  });

  it("is hidden when closed", () => {
    render(<ChatPanel open={false} onClose={vi.fn()} onActions={vi.fn()} />);
    expect(screen.getByTestId("chat-panel").hidden).toBe(true);
  });
});
