import { formatChangePercent, formatPrice, TONE_CLASS } from "@/lib/format";
import type { History } from "@/lib/history";
import type { WatchlistRow } from "@/lib/types";
import type { MarketError } from "@/lib/useMarket";

import { Sparkline } from "./Sparkline";
import { Button } from "./ui";

const ARROWS = {
  up: { glyph: "\u25b2", className: "text-brand-teal-ink", flash: "flash-up" },
  down: { glyph: "\u25bc", className: "text-brand-orange-ink", flash: "flash-down" },
};

function PriceCell({ quote, tick }: WatchlistRow) {
  const arrow = tick?.direction ? ARROWS[tick.direction] : null;
  const flash = arrow && tick && tick.flash > 0 ? arrow.flash : "";
  return (
    <td className="px-2 py-2 text-right whitespace-nowrap tabular-nums">
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

export function Watchlist({
  rows,
  error,
  onRemove,
  history,
  selected,
  onSelect,
}: {
  rows: WatchlistRow[] | null;
  error: MarketError;
  onRemove?: (ticker: string) => void;
  history?: History;
  selected?: string;
  onSelect?: (ticker: string) => void;
}) {
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
            {history && (
              <th scope="col" className="hidden px-2 py-2 text-right font-semibold sm:table-cell">
                Trend
              </th>
            )}
            {onRemove && (
              <th scope="col">
                <span className="sr-only">Remove</span>
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map(({ quote, tick }) => {
            const change = formatChangePercent(quote.day_change_percent);
            return (
              <tr key={quote.ticker} className="border-t border-stroke">
                <th scope="row" className="px-2 py-2 text-left font-semibold">
                  {onSelect ? (
                    <button
                      type="button"
                      aria-pressed={selected === quote.ticker}
                      onClick={() => onSelect(quote.ticker)}
                      className={`cursor-pointer font-semibold underline-offset-4 hover:underline ${selected === quote.ticker ? "text-brand-teal-ink underline" : ""}`}
                    >
                      {quote.ticker}
                    </button>
                  ) : (
                    quote.ticker
                  )}
                </th>
                <PriceCell quote={quote} tick={tick} />
                <td className={`px-2 py-2 text-right tabular-nums ${TONE_CLASS[change.tone]}`}>
                  {change.text}
                </td>
                {history && (
                  <td className="hidden px-2 text-right sm:table-cell">
                    <Sparkline points={history[quote.ticker] ?? []} />
                  </td>
                )}
                {onRemove && (
                  <td className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Remove ${quote.ticker}`}
                      onClick={() => onRemove(quote.ticker)}
                    >
                      {"\u2715"}
                    </Button>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
