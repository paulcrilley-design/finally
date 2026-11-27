const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const quantity = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 });
const MINUS = "−";
const NONE = "—";

/** `$10,000.00`; an em dash when there is no value. */
export function formatMoney(value: number | null | undefined): string {
  return value == null ? NONE : usd.format(value);
}

/** Sign always shown (+ or a true minus), so direction never relies on colour. */
function signed(value: number, text: (abs: number) => string): string {
  const rounded = Math.round(value * 100) / 100;
  const sign = rounded > 0 ? "+" : rounded < 0 ? MINUS : "";
  return sign + text(Math.abs(rounded));
}

export function formatSignedMoney(value: number | null | undefined): string {
  return value == null ? NONE : signed(value, (v) => usd.format(v));
}

export function formatPercent(value: number | null | undefined): string {
  return value == null ? NONE : signed(value, (v) => `${v.toFixed(2)}%`);
}

export function formatQuantity(value: number): string {
  return quantity.format(value);
}

export function formatTime(ms: number): string {
  return new Date(ms).toLocaleTimeString("en-GB");
}

export type PnlState = "profit" | "loss" | "flat";

export function pnlState(value: number | null | undefined): PnlState {
  // Rounded exactly as `signed` displays it, so a "0.00" label is never coloured as a gain or loss.
  const rounded = value == null ? 0 : Math.round(value * 100) / 100;
  if (rounded === 0) return "flat";
  return rounded > 0 ? "profit" : "loss";
}

export const PNL_TEXT: Record<PnlState, string> = {
  profit: "text-brand-teal-ink",
  loss: "text-brand-orange-ink",
  flat: "text-gray-text",
};
