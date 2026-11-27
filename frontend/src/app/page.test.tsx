import { act, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource } from "@/test/fakeEventSource";

import Page from "./page";

const TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

// ZZZZ has no price yet; the rest are priced 100.00, 101.00, ...
const WATCHLIST = [
  ...TICKERS.map((ticker, i) => ({ ticker, price: 100 + i })),
  { ticker: "ZZZZ", price: null },
];

function stubFetch(status = 200) {
  const fetchMock = vi.fn(async () => Response.json({ watchlist: WATCHLIST }, { status }));
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

async function renderLoaded() {
  const view = render(<Page />);
  await screen.findByRole("table");
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
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async () => source.emitOpen());
    await act(async () => source.emitOpen());
    expect(fetchMock).toHaveBeenCalledTimes(3);
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

  it("closes the stream when the page is left", async () => {
    const { source, unmount } = await renderLoaded();
    expect(source.readyState).not.toBe(FakeEventSource.CLOSED);
    unmount();
    expect(source.readyState).toBe(FakeEventSource.CLOSED);
  });
});
