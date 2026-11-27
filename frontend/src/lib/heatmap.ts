import { formatChangePercent, type Tone } from "./format";
import type { Position } from "./types";

export type Tile = { name: string; size: number; change: string; tone: Tone };

/** One tile per position with a known value, sized by that value. */
export function heatmapTiles(positions: Position[]): Tile[] {
  return positions.flatMap((position) => {
    if (position.market_value === null || position.market_value <= 0) return [];
    const { text, tone } = formatChangePercent(position.pnl_percent);
    return [{ name: position.ticker, size: position.market_value, change: text, tone }];
  });
}
