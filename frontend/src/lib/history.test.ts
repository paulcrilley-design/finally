import { describe, expect, it } from "vitest";

import { appendHistory, MAX_POINTS } from "./history";
import type { PriceMap } from "./types";

const at = (price: number, timestamp: number) =>
  ({ AAPL: { price, timestamp } }) as unknown as PriceMap;

describe("appendHistory", () => {
  it("starts empty and adds a point per new timestamp without mutating", () => {
    const first = appendHistory({}, at(100, 1));
    const second = appendHistory(first, at(101, 2));
    expect(second.AAPL).toEqual([
      { time: 1, price: 100 },
      { time: 2, price: 101 },
    ]);
    expect(first.AAPL).toHaveLength(1);
  });

  it("ignores repeated timestamps and unknown prices", () => {
    const first = appendHistory({}, at(100, 1));
    expect(appendHistory(first, at(105, 1))).toEqual(first);
    expect(appendHistory(first, { AAPL: {} } as unknown as PriceMap)).toEqual(first);
  });

  it("keeps only the newest points", () => {
    let history = {};
    for (let time = 1; time <= MAX_POINTS + 5; time++) {
      history = appendHistory(history, at(time, time));
    }
    const points = (history as ReturnType<typeof appendHistory>).AAPL;
    expect(points).toHaveLength(MAX_POINTS);
    expect(points[0].time).toBe(6);
  });
});
