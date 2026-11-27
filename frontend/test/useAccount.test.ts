import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useAccount } from "../src/lib/useAccount";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("keeps retrying while the server is down", async () => {
  vi.useFakeTimers();
  const fetchMock = vi.fn(async (_path: string) => {
    throw new TypeError("down");
  });
  vi.stubGlobal("fetch", fetchMock);

  renderHook(() => useAccount());
  await act(() => vi.advanceTimersByTimeAsync(0)); // let the first load fail
  for (let i = 0; i < 4; i++) await act(() => vi.advanceTimersByTimeAsync(5000));

  // The first load and one retry every 5 seconds.
  expect(fetchMock.mock.calls.filter(([path]) => path === "/api/portfolio")).toHaveLength(5);
});
