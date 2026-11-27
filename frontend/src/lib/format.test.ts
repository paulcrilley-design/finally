import { describe, expect, it } from "vitest";

import { formatChangePercent, formatPrice } from "./format";

describe("formatPrice", () => {
  it.each([
    [190, "190.00"],
    [1234.5, "1,234.50"],
    [2.675, "2.68"],
    [1.005, "1.01"],
    [null, "—"],
  ])("formats %s as %s", (value, text) => {
    expect(formatPrice(value)).toBe(text);
  });
});

describe("formatChangePercent", () => {
  it.each([
    [0.12, "+0.12%", "gain"],
    [-0.12, "−0.12%", "loss"],
    [0, "0.00%", "flat"],
    [-0, "0.00%", "flat"],
    [0.0049, "0.00%", "flat"],
    [-0.0049, "0.00%", "flat"],
    [0.005, "+0.01%", "gain"],
    [-0.005, "−0.01%", "loss"],
    [1.005, "+1.01%", "gain"],
    [null, "—", "flat"],
  ])("formats %s as %s (%s)", (value, text, tone) => {
    expect(formatChangePercent(value)).toEqual({ text, tone });
  });
});
