import type { Portfolio, PriceMap } from "./types";

/** Revalues a portfolio at the latest streamed prices (API values are the fallback). */
export function valuePortfolio(portfolio: Portfolio, prices: PriceMap): Portfolio {
  const priced = portfolio.positions.map((position) => {
    const price = prices[position.ticker]?.price ?? position.current_price;
    if (price == null) return position;
    const cost = position.quantity * position.avg_cost;
    const value = position.quantity * price;
    return {
      ...position,
      current_price: price,
      market_value: value,
      unrealized_pnl: value - cost,
      unrealized_pnl_percent: cost ? ((value - cost) / cost) * 100 : 0,
    };
  });
  const positionsValue = priced.reduce((sum, p) => sum + (p.market_value ?? 0), 0);
  return {
    cash_balance: portfolio.cash_balance,
    positions_value: positionsValue,
    total_value: portfolio.cash_balance + positionsValue,
    unrealized_pnl: priced.reduce((sum, p) => sum + (p.unrealized_pnl ?? 0), 0),
    positions: priced.map((p) => ({
      ...p,
      weight: p.market_value != null && positionsValue ? p.market_value / positionsValue : null,
    })),
  };
}
