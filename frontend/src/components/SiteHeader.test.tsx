import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteHeader } from "./SiteHeader";

describe("SiteHeader", () => {
  it("shows the logo, the product name and its children", () => {
    render(
      <SiteHeader>
        <span>status goes here</span>
      </SiteHeader>,
    );
    expect(screen.getByRole("img", { name: "openUI" })).toBeInTheDocument();
    expect(screen.getByText("FinAlly")).toBeInTheDocument();
    expect(screen.getByText("status goes here")).toBeInTheDocument();
  });
});
