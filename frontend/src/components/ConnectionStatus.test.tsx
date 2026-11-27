import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConnectionStatus } from "./ConnectionStatus";

describe("ConnectionStatus", () => {
  it.each([
    ["connected", "Connected", "bg-brand-teal-ink"],
    ["reconnecting", "Reconnecting", "bg-brand-orange"],
    ["disconnected", "Disconnected", "bg-brand-orange-ink"],
  ] as const)("shows %s in words with a coloured dot", (status, label, colour) => {
    render(<ConnectionStatus status={status} />);
    const element = screen.getByRole("status");
    expect(element).toHaveTextContent(label);
    expect(element.querySelector('[aria-hidden="true"]')).toHaveClass(colour);
  });
});
