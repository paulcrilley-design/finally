// Shared openUI components (planning/OUI_FORMAT.md section 4).
import type { ButtonHTMLAttributes, ComponentProps, ReactNode } from "react";

/** Joins class names, skipping empty ones. */
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

// Padding is a prop, not className: in Tailwind v4 the stylesheet order, not the
// class order, decides which of two conflicting utilities wins.
const SIZES: Record<Size, string> = { sm: "px-3 py-1.5", md: "px-4 py-2", lg: "px-5 py-3" };

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 rounded-full text-sm font-semibold transition " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-teal " +
  "disabled:cursor-not-allowed disabled:opacity-50";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-teal-ink text-white hover:brightness-110",
  secondary: "border border-stroke bg-white text-brand-teal-ink hover:border-brand-teal",
  ghost: "text-brand-teal-ink hover:bg-surface",
  danger: "border border-stroke bg-white text-brand-orange-ink hover:border-brand-orange",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      type={type}
      className={cn(BUTTON_BASE, SIZES[size], VARIANTS[variant], className)}
      {...props}
    />
  );
}

/** A white card. `padded={false}` for content that sets its own padding. */
export function Panel({
  className,
  padded = true,
  ...props
}: ComponentProps<"div"> & { padded?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-stroke bg-white shadow-panel",
        padded && "p-6",
        className,
      )}
      {...props}
    />
  );
}

/** The small uppercase label above a heading. */
export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-semibold tracking-[0.25em] text-brand-teal-ink uppercase">
      {children}
    </p>
  );
}

export const INPUT =
  "mt-1 block w-full rounded-xl border border-stroke bg-white px-3 py-2 text-sm text-navy-dark " +
  "placeholder:text-gray-text focus:border-brand-teal";

/** Page heading (h1) and section heading (h2) styles. */
export const HEADING = "font-display text-2xl font-semibold text-navy-dark";
export const SUBHEADING = "font-display text-xl font-semibold text-navy-dark";
