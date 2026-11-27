import type { ChatResponse, Portfolio, Side, Snapshot, Trade, WatchlistItem } from "./types";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("network", "Cannot reach the server.");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(
      data?.error?.code ?? "http_error",
      data?.error?.message ?? `Request failed (${response.status}).`,
    );
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export const api = {
  portfolio: () => request<Portfolio>("/api/portfolio"),
  history: () => request<{ history: Snapshot[] }>("/api/portfolio/history"),
  trade: (ticker: string, quantity: number, side: Side) =>
    request<{ trade: Trade; portfolio: Portfolio }>("/api/portfolio/trade", "POST", { ticker, quantity, side }),
  watchlist: () => request<{ tickers: WatchlistItem[] }>("/api/watchlist"),
  addTicker: (ticker: string) => request<WatchlistItem>("/api/watchlist", "POST", { ticker }),
  removeTicker: (ticker: string) => request<void>(`/api/watchlist/${encodeURIComponent(ticker)}`, "DELETE"),
  chat: (message: string) => request<ChatResponse>("/api/chat", "POST", { message }),
};

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}
