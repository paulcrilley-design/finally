import type { MarketError } from "@/lib/useMarket";
import type { WatchlistItem } from "@/lib/types";

const priceFormat = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function Watchlist({ rows, error }: { rows: WatchlistItem[] | null; error: MarketError }) {
  if (rows === null) {
    return <p>{error ? "Watchlist unavailable" : "Loading watchlist"}</p>;
  }
  return (
    <table>
      <caption>Watchlist</caption>
      <thead>
        <tr>
          <th scope="col">Ticker</th>
          <th scope="col">Price</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ ticker, price }) => (
          <tr key={ticker}>
            <th scope="row">{ticker}</th>
            <td>{price === null ? "—" : priceFormat.format(price)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
