import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { usePrices } from "../src/lib/usePrices";
import { price } from "./helpers";

class FakeEventSource {
  static CLOSED = 2;
  static all: FakeEventSource[] = [];
  readyState = 0;
  closed = false;
  onopen?: () => void;
  onerror?: () => void;
  onmessage?: (event: { data: string }) => void;
  constructor(public url: string) {
    FakeEventSource.all.push(this);
  }
  close() {
    this.closed = true;
  }
}

describe("usePrices", () => {
  it("tracks prices and the connection state, and reconnects after a closed stream", () => {
    vi.useFakeTimers();
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.all = [];
    const { result, unmount } = renderHook(() => usePrices());
    const source = FakeEventSource.all[0];
    expect(source.url).toBe("/api/stream/prices");
    expect(result.current.connection).toBe("reconnecting");

    act(() => source.onmessage!({ data: JSON.stringify({ AAPL: price("AAPL", 5) }) }));
    expect(result.current.connection).toBe("connected");
    expect(result.current.latest.AAPL.price).toBe(5);

    act(() => source.onerror!());
    expect(result.current.connection).toBe("reconnecting");

    source.readyState = FakeEventSource.CLOSED;
    act(() => source.onerror!());
    expect(result.current.connection).toBe("disconnected");
    act(() => vi.advanceTimersByTime(3000));
    expect(FakeEventSource.all).toHaveLength(2);

    unmount();
    expect(FakeEventSource.all[1].closed).toBe(true);
  });
});
