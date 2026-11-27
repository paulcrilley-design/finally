"use client";

import { useEffect, useMemo, useState } from "react";
import { valuePortfolio } from "../lib/portfolio";
import { useAccount } from "../lib/useAccount";
import { usePrices } from "../lib/usePrices";
import { Alert } from "./Card";
import { ChatPanel } from "./ChatPanel";
import { Heatmap } from "./Heatmap";
import { MainChart } from "./MainChart";
import { PnlChart } from "./PnlChart";
import { PositionsTable } from "./PositionsTable";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";
import { TradeBar } from "./TradeBar";
import { cn } from "./ui";
import { Watchlist } from "./Watchlist";

/** Matches Tailwind's `xl`, where the chat panel docks beside the content. */
const DESKTOP = "(min-width: 1280px)";

export function Workstation() {
  const { latest, history, connection } = usePrices();
  const account = useAccount();
  const [picked, setPicked] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    setChatOpen(window.matchMedia(DESKTOP).matches);
  }, []);

  const portfolio = useMemo(
    () => account.portfolio && valuePortfolio(account.portfolio, latest),
    [account.portfolio, latest],
  );
  const positions = portfolio?.positions ?? [];

  // Keep the picked ticker while it is still watched or held, otherwise the first watched one.
  const known = [...(account.watchlist ?? []), ...positions].map((item) => item.ticker);
  const selected = picked && known.includes(picked) ? picked : (known[0] ?? null);

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <SiteHeader
        totalValue={portfolio?.total_value ?? null}
        cash={portfolio?.cash_balance ?? null}
        connection={connection}
        chatOpen={chatOpen}
        onToggleChat={() => setChatOpen((open) => !open)}
      />
      <main className="mx-auto w-full max-w-[1500px] flex-1 px-6 py-4">
        {account.error && <Alert className="mb-4">{account.error} Retrying…</Alert>}
        <div className={cn("grid gap-4", chatOpen && "xl:grid-cols-[minmax(0,1fr)_320px]")}>
          <div className="grid min-w-0 content-start items-start gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
            <Watchlist
              items={account.watchlist}
              prices={latest}
              history={history}
              selected={selected}
              onSelect={setPicked}
              onChanged={account.refresh}
            />
            <div className="grid min-w-0 gap-4">
              <MainChart
                ticker={selected}
                points={selected ? (history[selected] ?? []) : []}
                live={selected ? latest[selected] : undefined}
              />
              <TradeBar selected={selected} onTraded={account.refresh} />
              <Heatmap positions={positions} />
              <PnlChart history={account.history} />
            </div>
            <div className="min-w-0 lg:col-span-2">
              <PositionsTable positions={positions} onSelect={setPicked} />
            </div>
          </div>
          <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} onActions={account.refresh} />
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
