import { describe, expect, it } from "vitest";

import { isProtectedPath } from "./protectedRoutes";

describe("isProtectedPath", () => {
  it.each(["/profile", "/my-tickets", "/promoter", "/admin/users", "/validation-stations/1/activity"])(
    "protects %s",
    (pathname) => expect(isProtectedPath(pathname)).toBe(true)
  );

  it.each(["/", "/events/1", "/events/1/rrpp", "/checkout/order-1"])(
    "keeps %s public",
    (pathname) => expect(isProtectedPath(pathname)).toBe(false)
  );

  it("protects event management", () => {
    expect(isProtectedPath("/events/1/manage")).toBe(true);
  });
});
