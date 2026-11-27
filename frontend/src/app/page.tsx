"use client";

import { Watchlist } from "@/components/Watchlist";
import { useMarket } from "@/lib/useMarket";

export default function Page() {
  const { rows, error } = useMarket();

  return (
    <main className="p-6">
      <h1 className="mb-4 font-display text-2xl font-semibold">FinAlly</h1>
      <Watchlist rows={rows} error={error} />
    </main>
  );
}
