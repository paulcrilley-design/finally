"use client";

import { useEffect, useState } from "react";

type Prices = Record<string, { price: number }>;
type WatchlistItem = { ticker: string; price: number | null };

const priceFormat = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export default function Page() {
  const [prices, setPrices] = useState<Prices>({});
  const [watchlist, setWatchlist] = useState<WatchlistItem[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function loadWatchlist() {
      try {
        const response = await fetch("/api/watchlist");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body: { watchlist: WatchlistItem[] } = await response.json();
        if (mounted) setWatchlist(body.watchlist);
      } catch {
        if (mounted) setFailed(true);
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

  return (
    <main>
      <h1>FinAlly</h1>
      {watchlist === null ? (
        <p>{failed ? "Watchlist unavailable" : "Loading watchlist"}</p>
      ) : (
        <table>
          <caption>Watchlist</caption>
          <thead>
            <tr>
              <th scope="col">Ticker</th>
              <th scope="col">Price</th>
            </tr>
          </thead>
          <tbody>
            {watchlist.map((item) => {
              const price = prices[item.ticker]?.price ?? item.price;
              return (
                <tr key={item.ticker}>
                  <th scope="row">{item.ticker}</th>
                  <td>{price === null ? "—" : priceFormat.format(price)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </main>
  );
}
