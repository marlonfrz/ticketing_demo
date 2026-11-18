import { describe, expect, it } from "vitest";

import { getSafeRedirect } from "./safeRedirect";

const ORIGIN = "https://tickets.example";

describe("getSafeRedirect", () => {
  it("keeps internal paths with search parameters", () => {
    expect(getSafeRedirect("/profile?tab=orders", ORIGIN)).toBe(
      "/profile?tab=orders"
    );
  });

  it.each([
    "https://evil.example",
    "//evil.example",
    "/\\evil.example",
    "javascript:alert(1)",
  ])("rejects unsafe destination %s", (destination) => {
    expect(getSafeRedirect(destination, ORIGIN)).toBeNull();
  });
});
