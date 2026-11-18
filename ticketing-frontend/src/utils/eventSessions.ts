import type { Event, EventSession } from "../types/domain";

const ACTIVE_SESSION_STATUSES = new Set([
  "not_reviewed",
  "in_review",
  "draft",
  "published",
  "unpublished",
  "sold_out",
]);

export function getNextEventSession(event: Pick<Event, "sessions">): EventSession | null {
  const sessions = event?.sessions || [];
  const upcomingSessions = sessions
    .filter((session) => ACTIVE_SESSION_STATUSES.has(session.status))
    .sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());

  return upcomingSessions[0] || sessions[0] || null;
}

export function getLatestEventSession(event: Pick<Event, "sessions">): EventSession | null {
  return [...(event?.sessions || [])].sort(
    (a, b) => new Date(b.starts_at).getTime() - new Date(a.starts_at).getTime()
  )[0] || null;
}
