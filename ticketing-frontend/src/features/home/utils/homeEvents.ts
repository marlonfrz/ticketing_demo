import type { Event } from "../../../types/domain";

const FEATURED_SESSION_STATUSES = new Set(["published", "sold_out"]);

export function getFeaturedEvents(events: Event[]): Event[] {
  return events.filter(
    (event) =>
      event.status === "published" &&
      event.sessions.some((session) =>
        FEATURED_SESSION_STATUSES.has(session.status)
      )
  );
}

export function getVisibleEvents(events: Event[], visibleCount: number): Event[] {
  return events.slice(0, Math.max(0, visibleCount));
}
