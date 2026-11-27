import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatPrice } from "@/lib/format";

const clock = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

const AXIS = { fill: "var(--gray-text)", fontSize: 12 };

// A very flat series gets two cents of room each side, or the axis repeats its labels.
export function valueDomain(values: number[]): [number | "auto", number | "auto"] {
  const low = Math.round(Math.min(...values) * 100);
  const high = Math.round(Math.max(...values) * 100);
  return high - low < 4 ? [(low - 2) / 100, (high + 2) / 100] : ["auto", "auto"];
}

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
            domain={valueDomain(points.map((point) => point.value))}
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
