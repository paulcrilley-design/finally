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

const upToFour = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 });
const twoToFour = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

export const formatQuantity = (value: number) => upToFour.format(value);
export const formatCost = (value: number) => twoToFour.format(value);

// The sign is chosen after rounding, so "-0.00%" can never appear.
export function formatSigned(value: number | null, suffix = ""): { text: string; tone: Tone } {
  if (value == null) return { text: UNKNOWN, tone: "flat" };
  const size = twoDecimals.format(Math.abs(value));
  if (size === "0.00") return { text: `0.00${suffix}`, tone: "flat" };
  return value > 0
    ? { text: `+${size}${suffix}`, tone: "gain" }
    : { text: `${MINUS}${size}${suffix}`, tone: "loss" };
}

export const formatChangePercent = (value: number | null) => formatSigned(value, "%");

export const TONE_CLASS: Record<Tone, string> = {
  gain: "text-brand-teal-ink",
  loss: "text-brand-orange-ink",
  flat: "text-navy-dark",
};
