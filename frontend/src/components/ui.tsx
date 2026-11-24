/**
 * Shared UI in the openUI style, mirroring pm's components/ui.ts so both apps
 * look the same: pill buttons, rounded panels with a soft teal shadow,
 * uppercase eyebrows and Space Grotesk headings.
 */
import Link from "next/link";
import type {
  ButtonHTMLAttributes,
  ComponentProps,
  InputHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";

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

export function buttonClass(variant: Variant = "primary", size: Size = "md", className?: string): string {
  return cn(BUTTON_BASE, SIZES[size], VARIANTS[variant], className);
}

type ButtonStyle = { variant?: Variant; size?: Size };

export function Button({
  variant = "primary",
  size = "md",
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & ButtonStyle) {
  return <button type={type} className={buttonClass(variant, size, className)} {...props} />;
}

export function ButtonLink({ variant = "primary", size = "md", className, ...props }: ComponentProps<typeof Link> & ButtonStyle) {
  return <Link className={buttonClass(variant, size, className)} {...props} />;
}

export const PANEL = "rounded-3xl border border-stroke bg-white shadow-panel";

/**
 * A white card: pm's `panel`. Takes any div props (role, id, hidden, ref…);
 * `padded={false}` for content that sets its own padding, like lists.
 */
export function Panel({ className, padded = true, ...props }: ComponentProps<"div"> & { padded?: boolean }) {
  return <div className={cn(PANEL, padded && "p-6", className)} {...props} />;
}

/** The small uppercase label above a heading (pm spaces it wider on the sign-in card). */
export function Eyebrow({ wide = false, children }: { wide?: boolean; children: ReactNode }) {
  return (
    <p
      className={cn(
        "text-xs font-semibold text-brand-teal-ink uppercase",
        wide ? "tracking-[0.3em]" : "tracking-[0.25em]",
      )}
    >
      {children}
    </p>
  );
}

/** Page heading (h1) and section heading (h2) styles, as in pm. */
export const HEADING = "font-display text-2xl font-semibold text-navy-dark";
export const SUBHEADING = "font-display text-xl font-semibold text-navy-dark";

export function Spinner({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-sm font-semibold text-brand-teal-ink">
      <span className="size-5 animate-spin rounded-full border-2 border-stroke border-t-brand-teal" aria-hidden />
      {label}
    </div>
  );
}

/** A text input or textarea: pm's `input`. */
export const INPUT =
  "mt-1 block w-full rounded-xl border border-stroke bg-white px-3 py-2 text-sm text-navy-dark outline-none " +
  "transition placeholder:text-gray-text focus:border-brand-teal aria-invalid:border-brand-orange-ink";

type FieldProps = {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
};

function FieldFrame({ id, label, hint, error, optional, children }: FieldProps & { children: ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="flex items-baseline justify-between text-sm font-semibold text-navy-dark">
        {label}
        {optional && <span className="text-xs font-normal text-gray-text">Optional</span>}
      </label>
      {children}
      {error ? (
        <p id={`${id}-message`} className="mt-1 text-sm font-medium text-brand-orange-ink">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-message`} className="mt-1 text-xs text-gray-text">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

/** A labelled input with its hint or error wired up for screen readers. */
export function TextField({ id, label, hint, error, optional, ...input }: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <FieldFrame id={id} label={label} hint={hint} error={error} optional={optional}>
      <input
        id={id}
        aria-invalid={Boolean(error)}
        aria-describedby={error || hint ? `${id}-message` : undefined}
        className={INPUT}
        {...input}
      />
    </FieldFrame>
  );
}

export function TextAreaField({
  id,
  label,
  hint,
  error,
  optional,
  ...textarea
}: FieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <FieldFrame id={id} label={label} hint={hint} error={error} optional={optional}>
      <textarea
        id={id}
        aria-invalid={Boolean(error)}
        aria-describedby={error || hint ? `${id}-message` : undefined}
        className={INPUT}
        {...textarea}
      />
    </FieldFrame>
  );
}
