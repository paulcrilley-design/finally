"use client";

import { useEffect, useState } from "react";
import { applyPrices, EMPTY_PRICES, type PriceState } from "./prices";

export type ConnectionState = "connected" | "reconnecting" | "disconnected";

const RETRY_MS = 3000;

/** Subscribes to the SSE price stream and tracks the connection state. */
export function usePrices(url = "/api/stream/prices") {
  const [prices, setPrices] = useState<PriceState>(EMPTY_PRICES);
  const [connection, setConnection] = useState<ConnectionState>("reconnecting");

  useEffect(() => {
    let source: EventSource;
    let retry: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      source = new EventSource(url);
      source.onopen = () => setConnection("connected");
      source.onmessage = (event) => {
        setConnection("connected");
        const data = JSON.parse(event.data);
        setPrices((state) => applyPrices(state, data));
      };
      source.onerror = () => {
        // CLOSED means the browser has given up, so open a new connection ourselves.
        if (source.readyState === EventSource.CLOSED) {
          setConnection("disconnected");
          retry = setTimeout(connect, RETRY_MS);
        } else {
          setConnection("reconnecting");
        }
      };
    };

    connect();
    return () => {
      clearTimeout(retry);
      source.close();
    };
  }, [url]);

  return { ...prices, connection };
}
