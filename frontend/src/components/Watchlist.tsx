import type { MarketError } from "@/lib/useMarket";
import type { WatchlistItem } from "@/lib/types";

const priceFormat = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function Watchlist({ rows, error }: { rows: WatchlistItem[] | null; error: MarketError }) {
  if (rows === null) {
    return <p className="text-sm text-gray-text">{error ? "Watchlist unavailable" : "Loading watchlist"}</p>;
  }
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">Watchlist</caption>
      <thead>
        <tr className="text-gray-text">
          <th scope="col" className="py-2 text-left font-semibold">
            Ticker
          </th>
          <th scope="col" className="py-2 text-right font-semibold">
            Price
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ ticker, price }) => (
          <tr key={ticker} className="border-t border-stroke">
            <th scope="row" className="py-2 text-left font-semibold">
              {ticker}
            </th>
            <td className="py-2 text-right tabular-nums">
              {price === null ? "—" : priceFormat.format(price)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
