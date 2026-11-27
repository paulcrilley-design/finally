import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatPrice } from "@/lib/format";

const clock = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

const AXIS = { fill: "var(--gray-text)", fontSize: 12 };

/** A dollar value over time. `time` is in milliseconds. */
export function TimeChart({ points }: { points: { time: number; value: number }[] }) {
  return (
    <div className="h-64" aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} accessibilityLayer={false}>
          <CartesianGrid stroke="var(--stroke)" vertical={false} />
          <XAxis
            dataKey="time"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(time: number) => clock.format(time)}
            tick={AXIS}
            stroke="var(--stroke)"
            minTickGap={32}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={(value: number) => formatPrice(value)}
            tick={AXIS}
            stroke="var(--stroke)"
            width={72}
          />
          <Tooltip
            formatter={(value) => [`$${formatPrice(Number(value))}`, "Value"]}
            labelFormatter={(time) => clock.format(Number(time))}
            isAnimationActive={false}
          />
          <Line
            dataKey="value"
            stroke="var(--brand-teal-ink)"
            strokeWidth={2}
            dot={points.length === 1}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
