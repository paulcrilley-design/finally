import { useEffect, useState } from "react";

import { openPriceStream } from "./priceStream";
import { applyPrices, applyWatchlist, EMPTY_MARKET } from "./ticks";
import type { StreamStatus, WatchlistItem, WatchlistResponse, WatchlistRow } from "./types";

export type MarketError = "unavailable" | null;

// Rows follow the stored watchlist for order and membership, with streamed values on top.
export function useMarket(): {
  rows: WatchlistRow[] | null;
  status: StreamStatus;
  error: MarketError;
} {
  const [data, setData] = useState(EMPTY_MARKET);
  const [watchlist, setWatchlist] = useState<WatchlistItem[] | null>(null);
  const [status, setStatus] = useState<StreamStatus>("reconnecting");
  const [error, setError] = useState<MarketError>(null);

  useEffect(() => {
    let mounted = true;
    let latestRequest = 0;

    // A failure keeps the rows already shown.
    async function loadWatchlist() {
      const request = ++latestRequest;
      const current = () => mounted && request === latestRequest;
      try {
        const response = await fetch("/api/watchlist");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body: WatchlistResponse = await response.json();
        if (!current()) return;
        setWatchlist(body.watchlist);
        setData((previous) => applyWatchlist(previous, body.watchlist));
        setError(null);
      } catch {
        if (current()) setError("unavailable");
      }
    }
    loadWatchlist();

    // Prices are never cleared on disconnect: the last ones stay on screen.
    const close = openPriceStream(
      (prices) => setData((previous) => applyPrices(previous, prices)),
      (next) => {
        setStatus(next);
        if (next === "connected") loadWatchlist();
      },
    );
    return () => {
      mounted = false;
      close();
    };
  }, []);

  const rows =
    watchlist?.map((item) => ({
      quote: data.quotes[item.ticker] ?? item,
      tick: data.ticks[item.ticker],
    })) ?? null;
  return { rows, status, error };
}
