import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatMoney, formatPercent, formatTime, PNL_TEXT, pnlState } from "../lib/format";
import type { PricePoint } from "../lib/prices";
import type { PriceUpdate } from "../lib/types";
import { Card, Empty } from "./Card";
import { AXIS, TOOLTIP } from "./chart";
import { cn } from "./ui";

export function MainChart({
  ticker,
  points,
  live,
}: {
  ticker: string | null;
  points: PricePoint[];
  live: PriceUpdate | undefined;
}) {
  return (
    <Card
      title={ticker ? `${ticker} price` : "Price chart"}
      data-testid="main-chart"
      data-ticker={ticker ?? ""}
      aside={
        live && (
          <p className="text-sm font-semibold tabular-nums">
            {formatMoney(live.price)}{" "}
            <span className={cn("text-xs", PNL_TEXT[pnlState(live.day_change_percent)])}>
              {formatPercent(live.day_change_percent)} today
            </span>
          </p>
        )
      }
    >
      <div className="h-64">
        {points.length < 2 ? (
          <Empty>{ticker ? "Waiting for prices…" : "Select a ticker in the watchlist."}</Empty>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--stroke)" vertical={false} />
              <XAxis dataKey="time" type="number" domain={["dataMin", "dataMax"]} tickFormatter={formatTime} minTickGap={48} {...AXIS} />
              <YAxis
                // At least ten cents of range, so the tick labels stay distinct.
                domain={[(min: number) => min - 0.05, (max: number) => max + 0.05]}
                tickFormatter={(v: number) => v.toFixed(2)}
                width={64}
                {...AXIS}
              />
              <Tooltip
                {...TOOLTIP}
                labelFormatter={(time) => formatTime(Number(time))}
                formatter={(value) => [formatMoney(Number(value)), "Price"]}
              />
              <Line dataKey="price" stroke="var(--brand-teal-ink)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
