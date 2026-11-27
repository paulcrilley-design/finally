"use client";

import { useState, type ReactNode } from "react";

import { AddTicker } from "@/components/AddTicker";
import { ConnectionStatus } from "@/components/ConnectionStatus";
import { PortfolioSummary } from "@/components/PortfolioSummary";
import { PositionsTable } from "@/components/PositionsTable";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { TradeBar } from "@/components/TradeBar";
import { Eyebrow, HEADING, Panel, SUBHEADING } from "@/components/ui";
import { Watchlist } from "@/components/Watchlist";
import { useMarket } from "@/lib/useMarket";
import { usePortfolio } from "@/lib/usePortfolio";
import { valuePortfolio } from "@/lib/valuation";

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={`${id}-heading`} className="min-w-0">
      <Panel>
        <h2 id={`${id}-heading`} className={`mb-4 ${SUBHEADING}`}>
          {title}
        </h2>
        {children}
      </Panel>
    </section>
  );
}

export default function Page() {
  const { rows, quotes, status, error, addTicker, removeTicker } = useMarket();
  const { portfolio, failed, trade } = usePortfolio(status);
  const valued = portfolio && valuePortfolio(portfolio, quotes);
  const [removeError, setRemoveError] = useState("");

  async function remove(ticker: string) {
    setRemoveError("");
    try {
      await removeTicker(ticker);
    } catch (failure) {
      setRemoveError((failure as Error).message);
    }
  }

  return (
    <>
      <a
        href="#watchlist"
        className="sr-only text-sm font-semibold text-brand-teal-ink focus:not-sr-only focus:bg-white focus:px-6 focus:py-3 focus-visible:-outline-offset-2"
      >
        Skip to watchlist
      </a>
      <SiteHeader>
        <div className="flex flex-wrap items-center gap-6">
          <PortfolioSummary portfolio={valued} />
          <ConnectionStatus status={status} />
        </div>
      </SiteHeader>
      <main className="mx-auto grid w-full max-w-[1500px] flex-1 content-start gap-6 p-6 lg:grid-cols-2">
        <section
          id="watchlist"
          tabIndex={-1}
          aria-labelledby="watchlist-heading"
          className="min-w-0"
        >
          <Panel>
            <Eyebrow>Live market</Eyebrow>
            <h1 id="watchlist-heading" className={`mt-1 mb-4 ${HEADING}`}>
              Watchlist
            </h1>
            <AddTicker onAdd={addTicker} />
            {removeError && (
              <p role="alert" className="mb-2 text-sm font-semibold text-brand-orange-ink">
                {removeError}
              </p>
            )}
            <Watchlist rows={rows} error={error} onRemove={remove} />
          </Panel>
        </section>
        <div className="grid min-w-0 content-start gap-6">
          <Section id="trade" title="Trade">
            <TradeBar onTrade={trade} />
          </Section>
          <Section id="positions" title="Positions">
            <PositionsTable positions={valued?.positions ?? null} failed={failed} />
          </Section>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
