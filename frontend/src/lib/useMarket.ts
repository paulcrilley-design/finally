import { useEffect, useState } from "react";

import { applyPrices, applyWatchlist, EMPTY_MARKET } from "./ticks";
import type { WatchlistItem, WatchlistResponse, WatchlistRow } from "./types";

export type MarketError = "unavailable" | null;

// Rows follow the stored watchlist for order and membership, with streamed values on top.
export function useMarket(): { rows: WatchlistRow[] | null; error: MarketError } {
  const [data, setData] = useState(EMPTY_MARKET);
  const [watchlist, setWatchlist] = useState<WatchlistItem[] | null>(null);
  const [error, setError] = useState<MarketError>(null);

  useEffect(() => {
    let mounted = true;
    async function loadWatchlist() {
      try {
        const response = await fetch("/api/watchlist");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body: WatchlistResponse = await response.json();
        if (!mounted) return;
        setWatchlist(body.watchlist);
        setData((current) => applyWatchlist(current, body.watchlist));
      } catch {
        if (mounted) setError("unavailable");
      }
    }
    loadWatchlist();

    const source = new EventSource("/api/stream/prices");
    source.onmessage = (event) => {
      try {
        const prices = JSON.parse(event.data);
        setData((current) => applyPrices(current, prices));
      } catch {
        // Ignore malformed data; the next message replaces it.
      }
    };
    return () => {
      mounted = false;
      source.close();
    };
  }, []);

  const rows =
    watchlist?.map((item) => ({
      quote: data.quotes[item.ticker] ?? item,
      tick: data.ticks[item.ticker],
    })) ?? null;
  return { rows, error };
}
