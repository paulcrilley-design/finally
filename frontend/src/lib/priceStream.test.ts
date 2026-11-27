import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource } from "@/test/fakeEventSource";

import { openPriceStream } from "./priceStream";

const { CONNECTING, CLOSED } = FakeEventSource;

describe("openPriceStream", () => {
  const onPrices = vi.fn();
  const onStatus = vi.fn();
  let close: () => void;

  const status = () => onStatus.mock.lastCall?.[0];
  const sources = () => FakeEventSource.instances;
  const latest = () => sources()[sources().length - 1];
  const advance = (ms: number) => vi.advanceTimersByTime(ms);

  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetAllMocks();
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
    close = openPriceStream(onPrices, onStatus);
  });

  afterEach(() => {
    close();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("starts as reconnecting and connects on open", () => {
    expect(latest().url).toBe("/api/stream/prices");
    expect(status()).toBe("reconnecting");
    latest().emitOpen();
    expect(status()).toBe("connected");
    expect(vi.getTimerCount()).toBe(0);
  });

  it("reports disconnected after exactly 10 s down", () => {
    latest().emitOpen();
    latest().emitError(CONNECTING);
    expect(status()).toBe("reconnecting");
    advance(9_999);
    expect(status()).toBe("reconnecting");
    advance(1);
    expect(status()).toBe("disconnected");
  });

  it("does not restart the clock on a second error", () => {
    latest().emitOpen();
    latest().emitError(CONNECTING);
    advance(5_000);
    latest().emitError(CONNECTING);
    advance(5_000);
    expect(status()).toBe("disconnected");
  });

  it("stays disconnected through later retries until it opens", () => {
    latest().emitOpen();
    latest().emitError(CONNECTING);
    advance(10_000);
    onStatus.mockClear();
    advance(1_000);
    latest().emitError(CONNECTING);
    advance(14_000);
    latest().emitError(CONNECTING);
    expect(onStatus).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);

    latest().emitOpen();
    expect(status()).toBe("connected");
    latest().emitError(CONNECTING);
    expect(status()).toBe("reconnecting");
    advance(10_000);
    expect(status()).toBe("disconnected");
  });

  it("replaces a closed source after 2 s", () => {
    const first = latest();
    first.emitOpen();
    first.emitError(CLOSED);
    expect(status()).toBe("disconnected");
    advance(1_999);
    expect(sources()).toHaveLength(1);
    advance(1);
    expect(sources()).toHaveLength(2);
    expect(first.readyState).toBe(CLOSED);
    latest().emitOpen();
    expect(status()).toBe("connected");
  });

  it("stays disconnected while a recreated source fails", () => {
    latest().emitError(CLOSED);
    advance(2_000);
    onStatus.mockClear();
    latest().emitError(CONNECTING);
    expect(onStatus).not.toHaveBeenCalled();
    latest().emitError(CLOSED);
    expect(status()).toBe("disconnected");
    advance(2_000);
    expect(sources()).toHaveLength(3);
    expect(sources().filter((source) => source.readyState !== CLOSED)).toHaveLength(1);
  });

  it("leaves nothing behind after cleanup", () => {
    latest().emitError(CLOSED);
    close();
    advance(60_000);
    expect(sources()).toHaveLength(1);
    expect(latest().readyState).toBe(CLOSED);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("passes on prices and ignores a malformed message", () => {
    latest().emitMessage("{not json");
    expect(onPrices).not.toHaveBeenCalled();
    latest().emitMessage('{"AAPL":{"price":1}}');
    expect(onPrices).toHaveBeenCalledWith({ AAPL: { price: 1 } });
  });
});
