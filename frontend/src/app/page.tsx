"use client";

import { useEffect, useState } from "react";

type Prices = Record<string, { price: number }>;

const priceFormat = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export default function Page() {
  const [prices, setPrices] = useState<Prices | null>(null);

  useEffect(() => {
    const source = new EventSource("/api/stream/prices");
    source.onmessage = (event) => {
      try {
        setPrices(JSON.parse(event.data));
      } catch {
        // Ignore malformed data; the next message replaces it.
      }
    };
    return () => source.close();
  }, []);

  return (
    <main>
      <h1>FinAlly</h1>
      {prices === null ? (
        <p>Loading watchlist</p>
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
            {Object.entries(prices).map(([ticker, { price }]) => (
              <tr key={ticker}>
                <th scope="row">{ticker}</th>
                <td>{priceFormat.format(price)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
