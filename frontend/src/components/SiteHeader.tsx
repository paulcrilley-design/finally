import type { ReactNode } from "react";

import { Logo } from "./Logo";
import { SUBHEADING } from "./ui";

/** Logo and product name on the left, any status on the right. */
export function SiteHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="border-b border-stroke bg-white/90">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-4">
          <Logo width={140} />
          <span className={SUBHEADING}>FinAlly</span>
        </div>
        {children}
      </div>
    </header>
  );
}
