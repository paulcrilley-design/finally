import {
  formatChangePercent,
  formatCost,
  formatPrice,
  formatQuantity,
  formatSigned,
  TONE_CLASS,
} from "@/lib/format";
import type { Position } from "@/lib/types";

const HEADERS = ["Quantity", "Average cost", "Price", "Unrealised P&L", "% change"];
const CELL = "px-2 py-2 text-right tabular-nums";

export function PositionsTable({
  positions,
  failed,
}: {
  positions: Position[] | null;
  failed: boolean;
}) {
  if (positions === null || positions.length === 0) {
    const empty = positions === null ? "Loading positions" : "No positions yet";
    return (
      <p className="text-sm text-gray-text">
        {positions === null && failed ? "Positions unavailable" : empty}
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="sr-only">Positions</caption>
        <thead>
          <tr className="bg-surface text-gray-text">
            <th scope="col" className="px-2 py-2 text-left font-semibold">
              Ticker
            </th>
            {HEADERS.map((header) => (
              <th key={header} scope="col" className="px-2 py-2 text-right font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => {
            const pnl = formatSigned(position.unrealized_pnl);
            const percent = formatChangePercent(position.pnl_percent);
            return (
              <tr key={position.ticker} className="border-t border-stroke">
                <th scope="row" className="px-2 py-2 text-left font-semibold">
                  {position.ticker}
                </th>
                <td className={CELL}>{formatQuantity(position.quantity)}</td>
                <td className={CELL}>{formatCost(position.avg_cost)}</td>
                <td className={CELL}>{formatPrice(position.price)}</td>
                <td className={`${CELL} ${TONE_CLASS[pnl.tone]}`}>{pnl.text}</td>
                <td className={`${CELL} ${TONE_CLASS[percent.tone]}`}>{percent.text}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
