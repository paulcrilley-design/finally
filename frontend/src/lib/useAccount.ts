"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "./api";
import type { Portfolio, Snapshot, WatchlistItem } from "./types";

const HISTORY_MS = 30_000;

/** Portfolio, watchlist and value history from the REST API. */
export function useAccount() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[] | null>(null);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refreshHistory = useCallback(async () => {
    try {
      setHistory((await api.history()).history);
    } catch {
      // Tried again on the next tick; the other requests report outages.
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [nextPortfolio, nextWatchlist] = await Promise.all([api.portfolio(), api.watchlist(), refreshHistory()]);
      setPortfolio(nextPortfolio);
      setWatchlist(nextWatchlist.tickers);
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }, [refreshHistory]);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refreshHistory(), HISTORY_MS);
    return () => clearInterval(timer);
  }, [refresh, refreshHistory]);

  // Keep trying while the first load has not succeeded.
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => void refresh(), 5000);
    return () => clearTimeout(timer);
  }, [error, refresh]);

  return { portfolio, watchlist, history, error, refresh };
}
