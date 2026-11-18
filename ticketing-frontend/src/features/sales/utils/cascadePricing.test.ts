import { describe, expect, it } from "vitest";

import type { SalesTicketOption } from "../api/salesApi";
import { calculateSelectionSubtotal } from "./cascadePricing";

function ticket(
  overrides: Partial<SalesTicketOption> = {}
): SalesTicketOption {
  return {
    id: "ticket-1",
    name: "General",
    description: null,
    price: "15.00",
    currency: "EUR",
    status: "published",
    sale_starts_at: null,
    sale_ends_at: null,
    sale_unlocked_at: "2026-08-07T10:00:00Z",
    display_order: 1,
    sale_order: 1,
    max_per_purchase: 10,
    max_selectable_quantity: 10,
    available_quantity: 10,
    availability_status: "available",
    is_low_stock: false,
    ...overrides,
  };
}

describe("calculateSelectionSubtotal", () => {
  it("uses the selected ticket price outside a cascade", () => {
    const selected = ticket();

    expect(calculateSelectionSubtotal(selected, 2, [selected])).toBe(30);
  });

  it("uses subsequent tier prices when the selection crosses stock", () => {
    const early = ticket({
      id: "early",
      sale_group_id: "group-1",
      sale_group_strategy: "stock_cascade",
      available_quantity: 1,
    });
    const general = ticket({
      id: "general",
      sale_group_id: "group-1",
      sale_group_strategy: "stock_cascade",
      sale_order: 2,
      sale_unlocked_at: null,
      price: "20.00",
      available_quantity: 5,
      max_selectable_quantity: 0,
      availability_status: "locked",
    });

    expect(calculateSelectionSubtotal(early, 3, [early, general])).toBe(55);
  });
});
