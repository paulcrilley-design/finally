// The server's formulas (backend value_position), in whole numbers so rounding matches exactly.

import type { Portfolio, Position, WatchlistItem } from "./types";

const units = (value: number, scale: number) => BigInt(Math.round(value * scale));

// Integer division rounding half away from zero. The divisor is positive.
function divide(value: bigint, by: bigint): bigint {
  const size = value < 0 ? -value : value;
  const rounded = (size * BigInt(2) + by) / (by * BigInt(2));
  return value < 0 ? -rounded : rounded;
}

const fromCents = (value: bigint) => Number(value) / 100;

export function valuePosition(position: Position, price: number | null): Position {
  if (price === null) {
    return { ...position, price, market_value: null, unrealized_pnl: null, pnl_percent: null };
  }
  const quantity = units(position.quantity, 10_000);
  const average = units(position.avg_cost, 10_000);
  const priceCents = units(price, 100);
  const value = divide(quantity * priceCents, BigInt(10_000));
  const cost = divide(quantity * average, BigInt(1_000_000));
  // Percent in hundredths: (price - average) / average, with both in ten-thousandths.
  const priceUnits = priceCents * BigInt(100);
  const percent =
    average > 0 ? fromCents(divide((priceUnits - average) * BigInt(10_000), average)) : null;
  return {
    ...position,
    price,
    market_value: fromCents(value),
    unrealized_pnl: fromCents(value - cost),
    pnl_percent: percent,
  };
}

/** The portfolio at the latest streamed prices. */
export function valuePortfolio(
  portfolio: Portfolio,
  quotes: Record<string, WatchlistItem>,
): Portfolio {
  const positions = portfolio.positions.map((position) =>
    valuePosition(position, quotes[position.ticker]?.price ?? position.price),
  );
  let total: bigint | null = units(portfolio.cash, 100);
  for (const { market_value } of positions) {
    total = total === null || market_value === null ? null : total + units(market_value, 100);
  }
  return { cash: portfolio.cash, total_value: total === null ? null : fromCents(total), positions };
}
