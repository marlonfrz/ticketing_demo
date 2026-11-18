import type { EntityId } from "../../../types/api";
import type { EventSession } from "../../../types/domain";

type SessionSelectionOptions = {
  includeUnpublished?: boolean;
  requestedSessionId?: EntityId | null;
  currentSessionId?: EntityId | null;
  now?: number;
};

export function selectEventSessionId(
  sessions: EventSession[] = [],
  {
    includeUnpublished = false,
    requestedSessionId = null,
    currentSessionId = null,
    now = Date.now(),
  }: SessionSelectionOptions = {}
): EntityId | null {
  const candidates = includeUnpublished
    ? sessions
    : sessions.filter((session) =>
        ["published", "sold_out", "finished"].includes(session.status)
      );

  for (const preferredId of [requestedSessionId, currentSessionId]) {
    if (preferredId && candidates.some((session) => session.id === preferredId)) {
      return preferredId;
    }
  }

  const withValidDate = candidates.filter((session) =>
    Number.isFinite(new Date(session.starts_at).getTime())
  );
  const upcoming = withValidDate
    .filter(
      (session) =>
        session.status !== "finished" &&
        new Date(session.starts_at).getTime() >= now
    )
    .sort(
      (a, b) =>
        new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime()
    );

  if (upcoming.length > 0) return upcoming[0]?.id ?? null;

  const closest = withValidDate.sort(
    (a, b) =>
      Math.abs(new Date(a.starts_at).getTime() - now) -
      Math.abs(new Date(b.starts_at).getTime() - now)
  );

  return closest[0]?.id ?? candidates[0]?.id ?? null;
}
