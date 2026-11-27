"use client";

import { Watchlist } from "@/components/Watchlist";
import { useMarket } from "@/lib/useMarket";

export default function Page() {
  const { rows, error } = useMarket();

  return (
    <main>
      <h1>FinAlly</h1>
      <Watchlist rows={rows} error={error} />
    </main>
  );
}
