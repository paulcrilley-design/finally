import "@testing-library/jest-dom/vitest";
import { createElement } from "react";
import { vi } from "vitest";

// next/image rejects a string src without a height outside production, and Vitest imports
// images as strings, so tests render a plain img.
vi.mock("next/image", () => ({
  default: ({
    src,
    priority,
    unoptimized,
    ...props
  }: Record<string, unknown> & { src: unknown }) => {
    void priority;
    void unoptimized;
    return createElement("img", { ...props, src: typeof src === "string" ? src : "logo.png" });
  },
}));
