import { formatMoney, formatPercent, formatQuantity, formatSignedMoney, PNL_TEXT, pnlState } from "../lib/format";
import type { Position } from "../lib/types";
import { Card, Empty } from "./Card";
import { cn } from "./ui";

const COLUMNS = ["Ticker", "Quantity", "Avg cost", "Price", "Unrealised P&L", "% change"];

export function PositionsTable({ positions, onSelect }: { positions: Position[]; onSelect: (ticker: string) => void }) {
  return (
    <Card title="Positions" data-testid="positions-table">
      {positions.length === 0 ? (
        <Empty>No open positions.</Empty>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm whitespace-nowrap tabular-nums">
            <thead className="bg-surface text-xs">
              <tr>
                {COLUMNS.map((column, i) => (
                  <th key={column} scope="col" className={cn("px-2 py-1.5 font-semibold", i ? "text-right" : "text-left")}>
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => {
                const colour = PNL_TEXT[pnlState(p.unrealized_pnl)];
                return (
                  <tr key={p.ticker} data-testid={`position-row-${p.ticker}`} className="border-t border-stroke text-right">
                    <th scope="row" className="px-2 py-1.5 text-left">
                      <button
                        type="button"
                        onClick={() => onSelect(p.ticker)}
                        className="rounded font-semibold text-brand-teal-ink hover:underline focus-visible:outline-2 focus-visible:outline-brand-teal"
                      >
                        {p.ticker}
                      </button>
                    </th>
                    <td data-testid={`position-quantity-${p.ticker}`} className="px-2">
                      {formatQuantity(p.quantity)}
                    </td>
                    <td className="px-2">{formatMoney(p.avg_cost)}</td>
                    <td className="px-2">{formatMoney(p.current_price)}</td>
                    <td className={cn("px-2", colour)}>{formatSignedMoney(p.unrealized_pnl)}</td>
                    <td className={cn("px-2", colour)}>{formatPercent(p.unrealized_pnl_percent)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
