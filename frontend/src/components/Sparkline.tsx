import { Line, LineChart, YAxis } from "recharts";

import type { PricePoint } from "@/lib/history";

/** Decoration beside the price: the numbers carry the meaning. */
export function Sparkline({ points }: { points: PricePoint[] }) {
  if (points.length < 2) return <span className="inline-block h-8 w-24" aria-hidden="true" />;
  return (
    <span className="inline-block" aria-hidden="true">
      <LineChart width={96} height={32} data={points} accessibilityLayer={false}>
        <YAxis hide domain={["dataMin", "dataMax"]} />
        <Line
          dataKey="price"
          stroke="var(--brand-teal-ink)"
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </span>
  );
}
