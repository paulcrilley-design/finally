import { formatChangePercent, formatPrice, type Tone } from "@/lib/format";
import type { WatchlistItem } from "@/lib/types";
import type { MarketError } from "@/lib/useMarket";

const TONE_CLASS: Record<Tone, string> = {
  gain: "text-brand-teal-ink",
  loss: "text-brand-orange-ink",
  flat: "text-navy-dark",
};

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
          <th scope="col" className="py-2 text-right font-semibold">
            Day change
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ ticker, price, day_change_percent }) => {
          const change = formatChangePercent(day_change_percent);
          return (
            <tr key={ticker} className="border-t border-stroke">
              <th scope="row" className="py-2 text-left font-semibold">
                {ticker}
              </th>
              <td className="py-2 text-right tabular-nums">{formatPrice(price)}</td>
              <td className={`py-2 text-right tabular-nums ${TONE_CLASS[change.tone]}`}>
                {change.text}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
