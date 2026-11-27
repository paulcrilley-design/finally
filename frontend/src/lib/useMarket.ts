import { useEffect, useState } from "react";

import type { PriceMap, WatchlistItem, WatchlistResponse } from "./types";

export type MarketError = "unavailable" | null;

// Rows follow the stored watchlist for order and membership, with streamed values on top.
export function useMarket(): { rows: WatchlistItem[] | null; error: MarketError } {
  const [prices, setPrices] = useState<PriceMap>({});
  const [watchlist, setWatchlist] = useState<WatchlistItem[] | null>(null);
  const [error, setError] = useState<MarketError>(null);

  useEffect(() => {
    let mounted = true;
    async function loadWatchlist() {
      try {
        const response = await fetch("/api/watchlist");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body: WatchlistResponse = await response.json();
        if (mounted) setWatchlist(body.watchlist);
      } catch {
        if (mounted) setError("unavailable");
      }
    }
    loadWatchlist();

    const source = new EventSource("/api/stream/prices");
    source.onmessage = (event) => {
      try {
        setPrices(JSON.parse(event.data));
      } catch {
        // Ignore malformed data; the next message replaces it.
      }
    };
    return () => {
      mounted = false;
      source.close();
    };
  }, []);

  const rows = watchlist?.map((item) => ({ ...item, ...prices[item.ticker] })) ?? null;
  return { rows, error };
}
