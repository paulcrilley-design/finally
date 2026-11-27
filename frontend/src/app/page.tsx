"use client";

import { ConnectionStatus } from "@/components/ConnectionStatus";
import { Watchlist } from "@/components/Watchlist";
import { useMarket } from "@/lib/useMarket";

export default function Page() {
  const { rows, status, error } = useMarket();

  return (
    <>
      <header className="flex justify-end border-b border-stroke bg-white px-6 py-4">
        <ConnectionStatus status={status} />
      </header>
      <main className="p-6">
        <h1 className="mb-4 font-display text-2xl font-semibold">FinAlly</h1>
        <Watchlist rows={rows} error={error} />
      </main>
    </>
  );
}
