import { describe, expect, it } from "vitest";

import type { Order } from "../../../types/domain";
import { matchesTicketSearch } from "./ticketSearch";

const order = {
  id: "12345678-abcd-efgh-ijkl-123456789012",
  tickets: [
    {
      ticket_code: "LOC-ABC-987",
      event: { title: "Festival de Música" },
    },
  ],
} as Order;

describe("matchesTicketSearch", () => {
  it("matches an event name without requiring accents", () => {
    expect(matchesTicketSearch(order, "musica")).toBe(true);
  });

  it("matches a ticket locator", () => {
    expect(matchesTicketSearch(order, "abc-987")).toBe(true);
  });

  it("matches the short order reference", () => {
    expect(matchesTicketSearch(order, "12345678")).toBe(true);
  });

  it("rejects unrelated searches", () => {
    expect(matchesTicketSearch(order, "otro evento")).toBe(false);
  });
});
