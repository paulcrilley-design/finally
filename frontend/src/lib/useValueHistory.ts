import { useEffect, useRef, useState } from "react";

import { request } from "./api";
import type { Portfolio, ValuePoint } from "./types";

const REFRESH_MS = 10_000;

/** The recorded values: reloaded every few seconds and whenever the server's portfolio changes. */
export function useValueHistory(portfolio: Portfolio | null) {
  const [history, setHistory] = useState<ValuePoint[] | null>(null);
  const [failed, setFailed] = useState(false);
  const latest = useRef(0); // only the newest response is applied

  useEffect(() => {
    const requests = latest;
    function load() {
      const mine = ++requests.current;
      request<{ history: ValuePoint[] }>("/api/portfolio/history").then(
        (body) => {
          if (mine !== requests.current) return;
          setHistory(body.history);
          setFailed(false);
        },
        () => {
          if (mine === requests.current) setFailed(true);
        },
      );
    }
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => {
      requests.current++;
      clearInterval(timer);
    };
  }, [portfolio]);

  return { history, failed };
}
