import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteFooter } from "./SiteFooter";

describe("SiteFooter", () => {
  it("says the money and prices are simulated", () => {
    render(<SiteFooter />);
    expect(screen.getByText(/money and prices shown are simulated/)).toBeInTheDocument();
  });
});
