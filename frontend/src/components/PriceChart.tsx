import { formatPrice } from "@/lib/format";
import type { PricePoint } from "@/lib/history";

import { TimeChart } from "./TimeChart";

export function PriceChart({ ticker, points }: { ticker: string; points: PricePoint[] }) {
  if (points.length === 0) {
    return <p className="text-sm text-gray-text">Waiting for {ticker} prices</p>;
  }
  const prices = points.map((point) => point.price);
  return (
    <>
      <p className="mb-2 text-sm text-gray-text">
        Latest ${formatPrice(prices[prices.length - 1])}, low ${formatPrice(Math.min(...prices))},
        high ${formatPrice(Math.max(...prices))} since this page opened.
      </p>
      <TimeChart points={points.map(({ time, price }) => ({ time: time * 1000, value: price }))} />
    </>
  );
}
