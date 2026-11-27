import { ResponsiveContainer, Treemap } from "recharts";

import type { Tone } from "@/lib/format";
import type { Tile } from "@/lib/heatmap";

// White text meets AA on all three.
const FILL: Record<Tone, string> = {
  gain: "var(--brand-teal-ink)",
  loss: "var(--brand-orange-ink)",
  flat: "var(--gray-text)",
};

type CellProps = Partial<Tile> & { x?: number; y?: number; width?: number; height?: number };

function Cell({ x = 0, y = 0, width = 0, height = 0, name, change, tone }: CellProps) {
  if (!tone) return <g />; // the treemap's root
  const roomy = width >= 64 && height >= 40;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={FILL[tone]}
        stroke="var(--surface-strong)"
        strokeWidth={2}
      />
      {roomy && (
        <text x={x + 8} y={y + 18} className="fill-white text-xs font-semibold">
          {name}
          <tspan x={x + 8} dy={16}>
            {change}
          </tspan>
        </text>
      )}
    </g>
  );
}

export function Heatmap({ tiles }: { tiles: Tile[] }) {
  if (tiles.length === 0) {
    return <p className="text-sm text-gray-text">No positions to show</p>;
  }
  return (
    <>
      <div className="h-56" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <Treemap data={tiles} dataKey="size" content={<Cell />} isAnimationActive={false} />
        </ResponsiveContainer>
      </div>
      {/* Small tiles have no label, and a drawing says nothing to a screen reader. */}
      <ul aria-label="Positions by size" className="sr-only">
        {[...tiles]
          .sort((a, b) => b.size - a.size)
          .map((tile) => (
            <li key={tile.name}>
              {tile.name} {tile.change}
            </li>
          ))}
      </ul>
    </>
  );
}
