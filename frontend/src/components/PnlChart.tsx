import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatMoney, formatTime } from "../lib/format";
import type { Snapshot } from "../lib/types";
import { Card, Empty } from "./Card";
import { AXIS, TOOLTIP } from "./chart";

export function PnlChart({ history }: { history: Snapshot[] }) {
  const data = history.map((s) => ({ time: Date.parse(s.recorded_at), value: s.total_value }));
  return (
    <Card title="Portfolio value" data-testid="pnl-chart" data-points={history.length}>
      <div className="h-56">
        {data.length === 0 ? (
          <Empty>No history yet.</Empty>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--stroke)" vertical={false} />
              <XAxis dataKey="time" type="number" domain={["dataMin", "dataMax"]} tickFormatter={formatTime} minTickGap={48} {...AXIS} />
              <YAxis
                domain={[(min: number) => Math.floor(min - 1), (max: number) => Math.ceil(max + 1)]}
                tickFormatter={(v: number) => `$${v.toLocaleString("en-US")}`}
                allowDecimals={false}
                width={72}
                {...AXIS}
              />
              <Tooltip
                {...TOOLTIP}
                labelFormatter={(time) => formatTime(Number(time))}
                formatter={(value) => [formatMoney(Number(value)), "Total value"]}
              />
              <Line dataKey="value" stroke="var(--brand-teal-ink)" strokeWidth={2} dot={data.length < 2} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
