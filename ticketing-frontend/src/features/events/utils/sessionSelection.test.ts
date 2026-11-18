import { describe, expect, it } from "vitest";

import { selectEventSessionId } from "./sessionSelection";
import type { EventSession } from "../../../types/domain";

function session(
  id: string,
  status: string,
  startsAt: string
): EventSession {
  return {
    id,
    status,
    starts_at: startsAt,
  } as EventSession;
}

describe("selectEventSessionId", () => {
  const sessions = [
    session("draft", "draft", "2026-07-10T12:00:00Z"),
    session("later", "published", "2026-07-20T12:00:00Z"),
    session("next", "published", "2026-07-15T12:00:00Z"),
  ];

  it("selects the next public session", () => {
    expect(
      selectEventSessionId(sessions, {
        now: new Date("2026-07-12T12:00:00Z").getTime(),
      })
    ).toBe("next");
  });

  it("ignores unpublished sessions in the public view", () => {
    expect(
      selectEventSessionId(sessions, {
        requestedSessionId: "draft",
        now: new Date("2026-07-12T12:00:00Z").getTime(),
      })
    ).toBe("next");
  });

  it("allows unpublished sessions in management", () => {
    expect(
      selectEventSessionId(sessions, {
        includeUnpublished: true,
        requestedSessionId: "draft",
      })
    ).toBe("draft");
  });
});
