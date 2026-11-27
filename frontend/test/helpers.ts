import { vi } from "vitest";
import type { PriceUpdate } from "../src/lib/types";

/** Stubs fetch with one JSON response and returns the mock. */
export function stubFetch(body: unknown, status = 200) {
  const mock = vi.fn().mockImplementation(async () => new Response(status === 204 ? null : JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", mock);
  return mock;
}

export function price(ticker: string, value: number, timestamp = 1, direction: PriceUpdate["direction"] = "up"): PriceUpdate {
  return {
    ticker,
    price: value,
    previous_price: value,
    timestamp,
    change: 0,
    change_percent: 0,
    direction,
    prev_close: value,
    day_change: 0,
    day_change_percent: 0,
  };
}
