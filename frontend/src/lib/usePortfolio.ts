import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, request } from "./api";
import type { Portfolio, StreamStatus, TradeOrder, TradeResponse } from "./types";

// Cash and positions come from the server: loaded at the start, on reconnect and after trades.
export function usePortfolio(status: StreamStatus) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [failed, setFailed] = useState(false);
  const latest = useRef(0); // only the newest response is applied

  const load = useCallback(() => {
    const mine = ++latest.current;
    request<Portfolio>("/api/portfolio").then(
      (body) => {
        if (mine !== latest.current) return;
        setPortfolio(body);
        setFailed(false);
      },
      () => {
        if (mine === latest.current) setFailed(true);
      },
    );
  }, []);

  const connected = status === "connected";
  useEffect(() => {
    load();
  }, [load, connected]);

  /** Resolves with the fill, or rejects with the message to show. */
  const trade = useCallback(
    async (order: TradeOrder): Promise<TradeResponse["trade"]> => {
      try {
        const body = await request<TradeResponse>("/api/portfolio/trade", "POST", order);
        latest.current++;
        setPortfolio(body.portfolio);
        return body.trade;
      } catch (error) {
        if (error instanceof ApiError) throw error;
        load(); // the order may have gone through: show what the server holds
        throw new Error("Trade not confirmed. Check your positions before trying again.");
      }
    },
    [load],
  );

  return { portfolio, failed, trade };
}
