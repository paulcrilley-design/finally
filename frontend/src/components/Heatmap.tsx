import { ResponsiveContainer, Treemap } from "recharts";
import { formatPercent, pnlState, type PnlState } from "../lib/format";
import type { Position } from "../lib/types";
import { Card, Empty } from "./Card";

const FILL: Record<PnlState, string> = {
  profit: "var(--brand-teal-ink)",
  loss: "var(--brand-orange-ink)",
  flat: "var(--gray-text)",
};

interface CellProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  depth?: number;
  name?: string;
  pnlPercent?: number | null;
}

/** One treemap rectangle: sized by market value, filled by P&L, labelled with a signed %. */
export function HeatmapCell({ x = 0, y = 0, width = 0, height = 0, depth, name, pnlPercent }: CellProps) {
  if (depth === 0 || !name) return <g />;
  const state = pnlState(pnlPercent);
  const centre = x + width / 2;
  return (
    <g data-testid={`heatmap-cell-${name}`} data-pnl={state}>
      <title>{`${name} ${formatPercent(pnlPercent)}`}</title>
      <rect x={x} y={y} width={width} height={height} rx={4} fill={FILL[state]} stroke="var(--surface-strong)" strokeWidth={2} />
      {width > 44 && height > 34 && (
        <g fill="var(--surface-strong)" textAnchor="middle" stroke="none">
          <text x={centre} y={y + height / 2 - 3} fontSize={13} fontWeight={600}>
            {name}
          </text>
          <text x={centre} y={y + height / 2 + 13} fontSize={11}>
            {formatPercent(pnlPercent)}
          </text>
        </g>
      )}
    </g>
  );
}

export function Heatmap({ positions }: { positions: Position[] }) {
  const data = positions
    .filter((p) => p.market_value != null && p.market_value > 0)
    .map((p) => ({ name: p.ticker, size: p.market_value!, pnlPercent: p.unrealized_pnl_percent }));
  return (
    <Card title="Portfolio heatmap" data-testid="heatmap" aside={<p className="text-xs text-gray-text">Size: value. Colour: P&amp;L.</p>}>
      <div className="h-56">
        {data.length === 0 ? (
          <Empty>No positions yet. Buy shares to fill the map.</Empty>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap data={data} dataKey="size" content={<HeatmapCell />} isAnimationActive={false} />
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
