import "@fontsource-variable/manrope";
import "@fontsource-variable/space-grotesk";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinAlly | Trading Workstation",
  description: "A simulated trading workstation with an AI assistant.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
