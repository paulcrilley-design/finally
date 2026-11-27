import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource } from "@/test/fakeEventSource";

import Page from "./page";

const TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

// ZZZZ has no price yet; the rest are priced 100.00, 101.00, ...
const WATCHLIST = [
  ...TICKERS.map((ticker, i) => ({ ticker, price: 100 + i })),
  { ticker: "ZZZZ", price: null },
];

const PORTFOLIO = { cash: 10000, total_value: 10000, positions: [] };

const AFTER_BUY = {
  cash: 9800,
  total_value: 10000,
  positions: [
    {
      ticker: "AAPL",
      quantity: 2,
      avg_cost: 100,
      price: 100,
      market_value: 200,
      unrealized_pnl: 0,
      pnl_percent: 0,
    },
  ],
};

function stubFetch(status = 200) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === "/api/portfolio") return Response.json(PORTFOLIO, { status });
    if (url === "/api/portfolio/trade") {
      const { quantity, side, ticker } = JSON.parse(init!.body as string);
      if (quantity !== 2) {
        const error = { code: "insufficient_cash", message: "Not enough cash." };
        return Response.json({ error }, { status: 400 });
      }
      const trade = { ticker, side, quantity, price: 100 };
      return Response.json({ trade, portfolio: AFTER_BUY });
    }
    if (init?.method === "DELETE") return Response.json({ watchlist: WATCHLIST.slice(1) });
    if (init?.method === "POST") {
      const added = { ticker: "PYPL", price: 65 };
      return Response.json({ watchlist: [...WATCHLIST, added] });
    }
    return Response.json({ watchlist: WATCHLIST }, { status });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// Cells are addressed by position: the price is the first cell of its row.
function priceCell(ticker: string) {
  const row = screen.getByRole("rowheader", { name: new RegExp(`^${ticker}\\b`) }).closest("tr");
  return within(row as HTMLElement).getAllByRole("cell")[0];
}

function rowTexts() {
  return screen.getAllByRole("row").map((row) => row.textContent);
}

const watchlistRequests = (fetchMock: ReturnType<typeof stubFetch>) =>
  fetchMock.mock.calls.filter(([url]) => url === "/api/watchlist").length;

async function renderLoaded() {
  const view = render(<Page />);
  await screen.findByRole("table", { name: "Watchlist" });
  return { ...view, source: FakeEventSource.instances[0] };
}

describe("Page", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
    stubFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a loading message before the watchlist arrives", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => {})));
    render(<Page />);
    expect(screen.getByText("Loading watchlist")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("lists the tickers in watchlist order", async () => {
    await renderLoaded();
    const tickers = screen.getAllByRole("rowheader").map((cell) => cell.textContent);
    expect(tickers).toEqual([...TICKERS, "ZZZZ"]);
    expect(priceCell("AAPL")).toHaveTextContent("100.00");
  });

  it("shows an em dash for an unknown price", async () => {
    await renderLoaded();
    expect(priceCell("ZZZZ")).toHaveTextContent("—");
  });

  it("replaces a price when the stream sends a new one", async () => {
    const { source } = await renderLoaded();
    expect(source.url).toBe("/api/stream/prices");
    act(() => source.emitMessage(JSON.stringify({ AAPL: { price: 191.5 } })));
    expect(priceCell("AAPL")).toHaveTextContent("191.50");
    expect(priceCell("GOOGL")).toHaveTextContent("101.00");
  });

  it("keeps every row unchanged on a malformed stream message", async () => {
    const { source } = await renderLoaded();
    act(() => source.emitMessage(JSON.stringify({ AAPL: { price: 191.5 } })));
    const before = rowTexts();
    expect(() => act(() => source.emitMessage("{not json"))).not.toThrow();
    expect(rowTexts()).toEqual(before);
  });

  it("says the watchlist is unavailable when the request fails", async () => {
    stubFetch(500);
    render(<Page />);
    expect(await screen.findByText("Watchlist unavailable")).toBeInTheDocument();
  });

  it("fetches the watchlist again on every open", async () => {
    const fetchMock = stubFetch();
    const { source } = await renderLoaded();
    expect(watchlistRequests(fetchMock)).toBe(1);
    await act(async () => source.emitOpen());
    await act(async () => source.emitOpen());
    expect(watchlistRequests(fetchMock)).toBe(3);
  });

  it("keeps the last prices through errors and a closed source", async () => {
    const { source } = await renderLoaded();
    act(() => source.emitMessage(JSON.stringify({ AAPL: { price: 191.5 } })));
    act(() => source.emitError(FakeEventSource.CONNECTING));
    act(() => source.emitError(FakeEventSource.CLOSED));
    expect(priceCell("AAPL")).toHaveTextContent("191.50");
  });

  it("shows rows when an open follows a failed first fetch", async () => {
    stubFetch(500);
    render(<Page />);
    await screen.findByText("Watchlist unavailable");
    stubFetch();
    await act(async () => FakeEventSource.instances[0].emitOpen());
    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect(priceCell("AAPL")).toHaveTextContent("100.00");
  });

  it("shows the connection state while keeping the last prices", async () => {
    const { source } = await renderLoaded();
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Reconnecting");
    await act(async () => source.emitOpen());
    expect(status).toHaveTextContent("Connected");
    act(() => source.emitMessage(JSON.stringify({ AAPL: { price: 191.5 } })));
    act(() => source.emitError(FakeEventSource.CLOSED));
    expect(status).toHaveTextContent("Disconnected");
    expect(priceCell("AAPL")).toHaveTextContent("191.50");
  });

  it("shows the logo, name and connection status in the banner", async () => {
    await renderLoaded();
    const banner = within(screen.getByRole("banner"));
    expect(banner.getByRole("img", { name: "openUI" })).toBeInTheDocument();
    expect(banner.getByText("FinAlly")).toBeInTheDocument();
    expect(banner.getByRole("status")).toHaveTextContent("Reconnecting");
  });

  it("starts with a skip link that leads to the watchlist", async () => {
    const { container } = await renderLoaded();
    const first = container.querySelector<HTMLElement>("a[href], button, input, [tabindex]");
    expect(first).toBe(screen.getByRole("link", { name: "Skip to watchlist" }));
    expect(first).toHaveAttribute("href", "#watchlist");
    const target = container.querySelector<HTMLElement>("#watchlist")!;
    target.focus();
    expect(target).toHaveFocus();
  });

  it("has one main landmark, heading and table, and the simulation notice", async () => {
    await renderLoaded();
    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Watchlist");
    expect(screen.getByRole("table", { name: "Watchlist" })).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toHaveTextContent(/simulated/);
  });

  function banner() {
    return screen.getByRole("banner");
  }

  async function submitTrade(quantity: string) {
    const form = within(screen.getByRole("form", { name: "Trade" }));
    fireEvent.change(form.getByLabelText("Ticker"), { target: { value: "aapl" } });
    fireEvent.change(form.getByLabelText("Quantity"), { target: { value: quantity } });
    await act(async () => fireEvent.click(form.getByRole("button", { name: "Buy" })));
  }

  it("shows cash and total value in the header", async () => {
    await renderLoaded();
    expect(banner()).toHaveTextContent("Total value$10,000.00");
    expect(banner()).toHaveTextContent("Cash$10,000.00");
  });

  it("shows a filled trade and keeps its values live", async () => {
    const { source } = await renderLoaded();
    await submitTrade("2");
    expect(screen.getByText("Bought 2 AAPL at $100.00.")).toBeInTheDocument();
    expect(banner()).toHaveTextContent("Cash$9,800.00");
    act(() => source.emitMessage(JSON.stringify({ AAPL: { price: 110 } })));
    const table = screen.getByRole("table", { name: "Positions" });
    const cells = within(table).getAllByRole("cell").map((cell) => cell.textContent);
    expect(cells).toEqual(["2", "100.00", "110.00", "+20.00", "+10.00%"]);
    expect(banner()).toHaveTextContent("Total value$10,020.00");
  });

  it("shows why a trade was refused and changes nothing", async () => {
    await renderLoaded();
    await submitTrade("500");
    expect(screen.getByRole("alert")).toHaveTextContent("Not enough cash.");
    expect(banner()).toHaveTextContent("Cash$10,000.00");
    expect(screen.getByText("No positions yet")).toBeInTheDocument();
  });

  it("adds and removes watchlist tickers", async () => {
    await renderLoaded();
    const form = within(screen.getByRole("form", { name: "Add to watchlist" }));
    fireEvent.change(form.getByLabelText("New ticker"), { target: { value: "pypl" } });
    await act(async () => fireEvent.click(form.getByRole("button", { name: "Add" })));
    expect(priceCell("PYPL")).toHaveTextContent("65.00");
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Remove AAPL" })));
    expect(screen.queryByRole("rowheader", { name: "AAPL" })).not.toBeInTheDocument();
  });

  it("closes the stream when the page is left", async () => {
    const { source, unmount } = await renderLoaded();
    expect(source.readyState).not.toBe(FakeEventSource.CLOSED);
    unmount();
    expect(source.readyState).toBe(FakeEventSource.CLOSED);
  });
});
