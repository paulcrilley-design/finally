"use client";

import { ConnectionStatus } from "@/components/ConnectionStatus";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { Eyebrow, HEADING, Panel } from "@/components/ui";
import { Watchlist } from "@/components/Watchlist";
import { useMarket } from "@/lib/useMarket";

export default function Page() {
  const { rows, status, error } = useMarket();

  return (
    <>
      <a
        href="#watchlist"
        className="sr-only text-sm font-semibold text-brand-teal-ink focus:not-sr-only focus:bg-white focus:px-6 focus:py-3 focus-visible:-outline-offset-2"
      >
        Skip to watchlist
      </a>
      <SiteHeader>
        <ConnectionStatus status={status} />
      </SiteHeader>
      <main className="mx-auto w-full max-w-[1500px] flex-1 p-6">
        <section id="watchlist" tabIndex={-1} aria-labelledby="watchlist-heading">
          <Panel>
            <Eyebrow>Live market</Eyebrow>
            <h1 id="watchlist-heading" className={`mt-1 mb-4 ${HEADING}`}>
              Watchlist
            </h1>
            <Watchlist rows={rows} error={error} />
          </Panel>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
