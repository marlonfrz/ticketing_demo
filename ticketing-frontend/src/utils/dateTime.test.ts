import { describe, expect, it } from "vitest";

import { formatEventDateTime } from "./dateTime";

describe("formatEventDateTime", () => {
  it("uses the Canary Islands time zone independently of the runtime locale", () => {
    expect(formatEventDateTime("2026-08-14T09:11:39Z")).toBe(
      "14 ago 2026, 10:11"
    );
  });
});
