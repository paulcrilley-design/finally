import type { Metadata } from "next";
import type { ReactNode } from "react";
// openUI fonts, self-hosted so builds need no network access.
import "@fontsource-variable/manrope";
import "@fontsource-variable/space-grotesk";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinAlly | Trading Workstation",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
