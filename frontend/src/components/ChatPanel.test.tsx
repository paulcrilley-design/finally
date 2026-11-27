import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ChatMessage } from "@/lib/types";

import { ChatPanel } from "./ChatPanel";

const messages: ChatMessage[] = [
  { id: "1", role: "user", content: "buy two", actions: null },
  {
    id: "2",
    role: "assistant",
    content: "Here you go.",
    actions: [
      {
        type: "trade",
        ticker: "AAPL",
        side: "buy",
        quantity: 2,
        price: 190,
        status: "executed",
        reason: "",
      },
      { type: "watchlist", ticker: "PYPL", action: "add", status: "executed", reason: "" },
      {
        type: "trade",
        ticker: "V",
        side: "sell",
        quantity: 1,
        status: "rejected",
        reason: "Not enough shares.",
      },
    ],
  },
];

function panel(props: Partial<Parameters<typeof ChatPanel>[0]> = {}) {
  const onSend = vi.fn(async () => true);
  render(<ChatPanel messages={[]} pending={null} error="" onSend={onSend} {...props} />);
  return { onSend, input: () => screen.getByLabelText("Message") };
}

async function submit(value: string) {
  fireEvent.change(screen.getByLabelText("Message"), { target: { value } });
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Send" })));
}

describe("ChatPanel", () => {
  it("shows the conversation with each action's outcome in words", () => {
    panel({ messages });
    expect(screen.getByRole("log")).toHaveTextContent("Here you go.");
    expect(screen.getByText("Bought 2 AAPL at $190.00")).toBeInTheDocument();
    expect(screen.getByText("Added PYPL to the watchlist")).toBeInTheDocument();
    expect(screen.getByText("Not done: sell 1 V. Not enough shares.")).toBeInTheDocument();
  });

  it("shows loading and blocks a second send", async () => {
    const { onSend } = panel({ pending: "hello" });
    expect(screen.getByText("Thinking…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
    expect(onSend).not.toHaveBeenCalled();
  });

  it("clears the input only when the message was answered", async () => {
    const failing = vi.fn(async () => false);
    const { input } = panel({ onSend: failing, error: "No key." });
    await submit("  hi  ");
    expect(failing).toHaveBeenCalledWith("hi");
    expect(input()).toHaveValue("  hi  ");
    expect(screen.getByRole("alert")).toHaveTextContent("No key.");
  });

  it("sends nothing when empty and clears after an answer", async () => {
    const { onSend, input } = panel();
    await submit("   ");
    expect(onSend).not.toHaveBeenCalled();
    await submit("hi");
    expect(input()).toHaveValue("");
  });

  it("collapses and reopens", () => {
    panel();
    fireEvent.click(screen.getByRole("button", { name: "Close chat" }));
    expect(screen.queryByRole("log")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open AI chat" }));
    expect(screen.getByRole("log")).toBeInTheDocument();
  });
});
