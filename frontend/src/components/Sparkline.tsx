import { Line, LineChart, YAxis } from "recharts";
import type { PricePoint } from "../lib/prices";

export function Sparkline({ points }: { points: PricePoint[] }) {
  if (points.length < 2) return <div className="h-7 w-16" aria-hidden />;
  return (
    <div aria-hidden>
      <LineChart width={64} height={28} data={points} margin={{ top: 2, right: 1, bottom: 2, left: 1 }}>
        <YAxis hide domain={["dataMin", "dataMax"]} />
        <Line dataKey="price" stroke="var(--brand-teal-ink)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </div>
  );
}
