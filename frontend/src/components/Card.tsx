import type { ComponentProps, ReactNode } from "react";
import { cn, PANEL, SUBHEADING } from "./ui";

/** A compact titled panel for the dense workstation layout. */
export function Card({
  title,
  aside,
  className,
  children,
  ...props
}: Omit<ComponentProps<"section">, "title"> & { title: string; aside?: ReactNode }) {
  return (
    <section className={cn(PANEL, "min-w-0 p-4", className)} aria-label={title} {...props}>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className={SUBHEADING}>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="flex h-full min-h-24 items-center justify-center text-center text-xs text-gray-text">{children}</p>;
}

export function Alert({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div role="alert" className={cn("rounded-2xl bg-brand-orange/10 px-4 py-2 text-sm text-brand-orange-ink", className)}>
      {children}
    </div>
  );
}
