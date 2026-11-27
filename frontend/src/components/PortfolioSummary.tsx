import { formatPrice } from "@/lib/format";
import type { Portfolio } from "@/lib/types";

/** Total value and cash for the header. A dash while unknown. */
export function PortfolioSummary({ portfolio }: { portfolio: Portfolio | null }) {
  const items = [
    ["Total value", portfolio?.total_value ?? null],
    ["Cash", portfolio?.cash ?? null],
  ] as const;
  return (
    <dl className="flex gap-6">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="text-xs text-gray-text">{label}</dt>
          <dd className="font-semibold tabular-nums">
            {value === null ? formatPrice(null) : `$${formatPrice(value)}`}
          </dd>
        </div>
      ))}
    </dl>
  );
}
