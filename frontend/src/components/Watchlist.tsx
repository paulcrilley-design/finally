import { formatChangePercent, formatPrice, type Tone } from "@/lib/format";
import type { WatchlistRow } from "@/lib/types";
import type { MarketError } from "@/lib/useMarket";

const TONE_CLASS: Record<Tone, string> = {
  gain: "text-brand-teal-ink",
  loss: "text-brand-orange-ink",
  flat: "text-navy-dark",
};

const ARROWS = {
  up: { glyph: "\u25b2", className: "text-brand-teal-ink", flash: "flash-up" },
  down: { glyph: "\u25bc", className: "text-brand-orange-ink", flash: "flash-down" },
};

function PriceCell({ quote, tick }: WatchlistRow) {
  const arrow = tick?.direction ? ARROWS[tick.direction] : null;
  const flash = arrow && tick && tick.flash > 0 ? arrow.flash : "";
  return (
    <td className="px-2 py-2 text-right tabular-nums">
      {arrow && (
        <>
          <span aria-hidden="true" className={`mr-1 text-xs ${arrow.className}`}>
            {arrow.glyph}
          </span>
          <span className="sr-only">{tick?.direction}</span>{" "}
        </>
      )}
      {/* A new key remounts the element, which restarts the animation. */}
      <span key={tick?.flash ?? 0} className={`rounded px-1 ${flash}`}>
        {formatPrice(quote.price)}
      </span>
    </td>
  );
}

export function Watchlist({ rows, error }: { rows: WatchlistRow[] | null; error: MarketError }) {
  if (rows === null) {
    return (
      <p className="text-sm text-gray-text">
        {error ? "Watchlist unavailable" : "Loading watchlist"}
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">Watchlist</caption>
        <thead>
          <tr className="bg-surface text-gray-text">
            <th scope="col" className="px-2 py-2 text-left font-semibold">
              Ticker
            </th>
            <th scope="col" className="px-2 py-2 text-right font-semibold">
              Price
            </th>
            <th scope="col" className="px-2 py-2 text-right font-semibold">
              Day change
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ quote, tick }) => {
            const change = formatChangePercent(quote.day_change_percent);
            return (
              <tr key={quote.ticker} className="border-t border-stroke">
                <th scope="row" className="px-2 py-2 text-left font-semibold">
                  {quote.ticker}
                </th>
                <PriceCell quote={quote} tick={tick} />
                <td className={`px-2 py-2 text-right tabular-nums ${TONE_CLASS[change.tone]}`}>
                  {change.text}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
