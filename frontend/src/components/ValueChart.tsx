import { formatPrice } from "@/lib/format";
import type { ValuePoint } from "@/lib/types";

import { TimeChart } from "./TimeChart";

export function ValueChart({ history, failed }: { history: ValuePoint[] | null; failed: boolean }) {
  if (history === null || history.length === 0) {
    const empty = history === null ? "Loading value history" : "No value history yet";
    return (
      <p className="text-sm text-gray-text">
        {history === null && failed ? "Value history unavailable" : empty}
      </p>
    );
  }
  const latest = history[history.length - 1].total_value;
  const count = history.length === 1 ? "1 point" : `${history.length} points`;
  return (
    <>
      <p className="mb-2 text-sm text-gray-text">
        Latest recorded value ${formatPrice(latest)}, {count} shown.
      </p>
      <TimeChart
        points={history.map((point) => ({
          time: Date.parse(point.recorded_at),
          value: point.total_value,
        }))}
      />
    </>
  );
}
