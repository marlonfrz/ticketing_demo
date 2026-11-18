import { describe, expect, it } from "vitest";

import { formatMoney } from "./money";

describe("formatMoney", () => {
  it("always displays two decimal places", () => {
    expect(formatMoney(19.5, "EUR")).toBe("19.50 EUR");
    expect(formatMoney("19.50", "EUR")).toBe("19.50 EUR");
    expect(formatMoney(0, "EUR")).toBe("0.00 EUR");
  });
});
