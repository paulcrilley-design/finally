"use client";

import { useState, type ReactNode } from "react";

import { AddTicker } from "@/components/AddTicker";
import { ConnectionStatus } from "@/components/ConnectionStatus";
import { Heatmap } from "@/components/Heatmap";
import { PortfolioSummary } from "@/components/PortfolioSummary";
import { PositionsTable } from "@/components/PositionsTable";
import { PriceChart } from "@/components/PriceChart";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { TradeBar } from "@/components/TradeBar";
import { Eyebrow, HEADING, Panel, SUBHEADING } from "@/components/ui";
import { ValueChart } from "@/components/ValueChart";
import { Watchlist } from "@/components/Watchlist";
import { heatmapTiles } from "@/lib/heatmap";
import { useMarket } from "@/lib/useMarket";
import { usePortfolio } from "@/lib/usePortfolio";
import { useValueHistory } from "@/lib/useValueHistory";
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
  const { rows, quotes, history, status, error, addTicker, removeTicker } = useMarket();
  const { portfolio, failed, trade } = usePortfolio(status);
  const valued = portfolio && valuePortfolio(portfolio, quotes);
  const [removeError, setRemoveError] = useState("");
  const values = useValueHistory(portfolio);
  const [chosen, setChosen] = useState("");
  // The chosen ticker while it is watched, otherwise the first one.
  const watched = rows?.map((row) => row.quote.ticker) ?? [];
  const selected = watched.includes(chosen) ? chosen : watched[0];

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
            <Watchlist
              rows={rows}
              error={error}
              onRemove={remove}
              history={history}
              selected={selected}
              onSelect={setChosen}
            />
          </Panel>
        </section>
        <div className="grid min-w-0 content-start gap-6">
          <Section id="chart" title={selected ? `${selected} price` : "Price"}>
            {selected ? (
              <PriceChart ticker={selected} points={history[selected] ?? []} />
            ) : (
              <p className="text-sm text-gray-text">No ticker to chart</p>
            )}
          </Section>
          <Section id="trade" title="Trade">
            <TradeBar onTrade={trade} />
          </Section>
          <Section id="positions" title="Positions">
            <PositionsTable positions={valued?.positions ?? null} failed={failed} />
          </Section>
          <Section id="heatmap" title="Heatmap">
            <Heatmap tiles={heatmapTiles(valued?.positions ?? [])} />
          </Section>
          <Section id="value" title="Portfolio value">
            <ValueChart history={values.history} failed={values.failed} />
          </Section>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
