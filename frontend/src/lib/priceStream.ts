// The price stream and its connection state. Framework free, so fake timers can test it.

import type { PriceMap, StreamStatus } from "./types";

export const DOWN_AFTER_MS = 10_000;
export const RECREATE_AFTER_MS = 2_000;

/** Opens the stream, replacing it whenever the browser gives up. Returns the cleanup. */
export function openPriceStream(
  onPrices: (prices: PriceMap) => void,
  onStatus: (status: StreamStatus) => void,
): () => void {
  let source: EventSource;
  // Set from the first failure until the next open: the record that the stream is down.
  let downTimer: ReturnType<typeof setTimeout> | undefined;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;

  function markDown() {
    if (downTimer !== undefined) return; // the 10 s clock never restarts
    onStatus("reconnecting");
    // The handle stays set after firing, so later retries report nothing.
    downTimer = setTimeout(() => onStatus("disconnected"), DOWN_AFTER_MS);
  }

  function connect() {
    source = new EventSource("/api/stream/prices");
    source.onopen = () => {
      clearTimeout(downTimer);
      clearTimeout(retryTimer);
      downTimer = undefined;
      onStatus("connected");
    };
    source.onmessage = (event) => {
      let prices: PriceMap;
      try {
        prices = JSON.parse(event.data);
      } catch {
        return; // ignore malformed data; the next message replaces it
      }
      onPrices(prices);
    };
    source.onerror = () => {
      markDown();
      // CLOSED means the browser will not retry by itself.
      if (source.readyState === EventSource.CLOSED) {
        onStatus("disconnected");
        source.close();
        clearTimeout(retryTimer);
        retryTimer = setTimeout(connect, RECREATE_AFTER_MS);
      }
    };
  }

  markDown(); // until the first open
  connect();

  return () => {
    clearTimeout(downTimer);
    clearTimeout(retryTimer);
    source.close();
  };
}
