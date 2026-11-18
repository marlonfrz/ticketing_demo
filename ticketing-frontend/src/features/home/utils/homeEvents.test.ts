import { describe, expect, it } from "vitest";

import type { Event, EventSession } from "../../../types/domain";
import { getFeaturedEvents, getVisibleEvents } from "./homeEvents";

const baseSession: EventSession = {
  id: "session-1",
  event_id: "event-1",
  title: null,
  location_name: "Auditorio",
  location_address: null,
  starts_at: "2026-08-15T20:00:00Z",
  ends_at: "2026-08-15T22:00:00Z",
  capacity: 500,
  status: "published",
  publish_at: "2026-07-15T10:00:00Z",
  tickets_publish_at: "2026-07-15T10:00:00Z",
  tickets_activated_at: "2026-07-15T10:00:00Z",
  display_order: 1,
  ticket_types_count: 2,
  sold_tickets_count: 0,
  created_at: "2026-07-15T10:00:00Z",
  updated_at: "2026-07-15T10:00:00Z",
};

function makeEvent(
  id: string,
  status = "published",
  sessionStatus = "published"
): Event {
  return {
    id,
    promoter_id: "promoter-1",
    title: `Evento ${id}`,
    description: "Descripción",
    status,
    sessions: [{ ...baseSession, id: `session-${id}`, event_id: id, status: sessionStatus }],
    created_at: "2026-07-15T10:00:00Z",
    updated_at: "2026-07-15T10:00:00Z",
  };
}

describe("getFeaturedEvents", () => {
  it("keeps only published events with a public active session", () => {
    const featured = getFeaturedEvents([
      makeEvent("active"),
      makeEvent("sold-out", "published", "sold_out"),
      makeEvent("finished", "finished", "finished"),
      makeEvent("without-active-session", "published", "finished"),
    ]);

    expect(featured.map((event) => event.id)).toEqual(["active", "sold-out"]);
  });
});

describe("getVisibleEvents", () => {
  it("returns events in batches without changing their order", () => {
    const events = Array.from({ length: 12 }, (_, index) =>
      makeEvent(String(index + 1))
    );

    expect(getVisibleEvents(events, 8)).toHaveLength(8);
    expect(getVisibleEvents(events, 16)).toHaveLength(12);
    expect(getVisibleEvents(events, 8)[0]?.id).toBe("1");
  });
});
