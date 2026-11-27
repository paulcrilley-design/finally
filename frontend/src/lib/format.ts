const twoDecimals = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const UNKNOWN = "—";
const MINUS = "−";

export function formatPrice(value: number | null): string {
  return value == null ? UNKNOWN : twoDecimals.format(value);
}

export type Tone = "gain" | "loss" | "flat";

// The sign is chosen after rounding, so "-0.00%" can never appear.
export function formatChangePercent(value: number | null): { text: string; tone: Tone } {
  if (value == null) return { text: UNKNOWN, tone: "flat" };
  const size = twoDecimals.format(Math.abs(value));
  if (size === "0.00") return { text: "0.00%", tone: "flat" };
  return value > 0
    ? { text: `+${size}%`, tone: "gain" }
    : { text: `${MINUS}${size}%`, tone: "loss" };
}
