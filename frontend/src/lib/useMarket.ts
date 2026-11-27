import { useCallback, useEffect, useRef, useState } from "react";

import { request } from "./api";
import { openPriceStream } from "./priceStream";
import { applyPrices, applyWatchlist, EMPTY_MARKET } from "./ticks";
import type { StreamStatus, WatchlistItem, WatchlistResponse, WatchlistRow } from "./types";

export type MarketError = "unavailable" | null;

// Rows follow the stored watchlist for order and membership, with streamed values on top.
export function useMarket() {
  const [data, setData] = useState(EMPTY_MARKET);
  const [watchlist, setWatchlist] = useState<WatchlistItem[] | null>(null);
  const [status, setStatus] = useState<StreamStatus>("reconnecting");
  const [error, setError] = useState<MarketError>(null);
  const latest = useRef(0); // only the newest watchlist response is applied

  const show = useCallback((body: WatchlistResponse) => {
    setWatchlist(body.watchlist);
    setData((previous) => applyWatchlist(previous, body.watchlist));
    setError(null);
  }, []);

  // A failure keeps the rows already shown.
  const load = useCallback(() => {
    const mine = ++latest.current;
    request<WatchlistResponse>("/api/watchlist").then(
      (body) => {
        if (mine === latest.current) show(body);
      },
      () => {
        if (mine === latest.current) setError("unavailable");
      },
    );
  }, [show]);

  useEffect(() => {
    const requests = latest;
    load();
    // Prices are never cleared on disconnect: the last ones stay on screen.
    const close = openPriceStream(
      (prices) => setData((previous) => applyPrices(previous, prices)),
      (next) => {
        setStatus(next);
        if (next === "connected") load();
      },
    );
    return () => {
      requests.current++; // ignore anything still in flight
      close();
    };
  }, [load]);

  const change = useCallback(
    async (path: string, method: string, body?: unknown) => {
      const response = await request<WatchlistResponse>(path, method, body);
      latest.current++;
      show(response);
    },
    [show],
  );
  const addTicker = useCallback(
    (ticker: string) => change("/api/watchlist", "POST", { ticker }),
    [change],
  );
  const removeTicker = useCallback(
    (ticker: string) => change(`/api/watchlist/${encodeURIComponent(ticker)}`, "DELETE"),
    [change],
  );

  const rows: WatchlistRow[] | null =
    watchlist?.map((item) => ({
      quote: data.quotes[item.ticker] ?? item,
      tick: data.ticks[item.ticker],
    })) ?? null;
  return { rows, quotes: data.quotes, status, error, addTicker, removeTicker };
}
