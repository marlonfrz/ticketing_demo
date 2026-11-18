import { afterEach, describe, expect, it, vi } from "vitest";

import {
  GUEST_CHECKOUT_COOKIE_MAX_AGE_SECONDS,
  classifyGuestCheckoutRoute,
  guestCheckoutCookieOptions,
  guestOrderCookieName,
  guestSessionCookieName,
  sanitizeReservationResponse,
} from "./guestCheckout";

describe("guest checkout server credentials", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("classifies only the checkout routes that may receive a guest credential", () => {
    expect(
      classifyGuestCheckoutRoute(
        ["events", "event-id", "reservations", "with-order"],
        "POST"
      )
    ).toEqual({ kind: "reservation" });
    expect(
      classifyGuestCheckoutRoute(
        ["payments", "demo", "checkout", "order-id"],
        "POST"
      )
    ).toEqual({ kind: "demo-checkout", orderId: "order-id" });
    expect(
      classifyGuestCheckoutRoute(
        ["payments", "demo", "confirm-session", "demo_session_123"],
        "POST"
      )
    ).toEqual({ kind: "demo-confirmation", sessionId: "demo_session_123" });
    expect(classifyGuestCheckoutRoute(["events"], "GET")).toBeNull();
  });

  it("removes the guest token from the response sent to browser JavaScript", () => {
    const original = {
      order_id: "order-id",
      guest_access_token: "guest_secret",
      status: "pending",
    };

    const result = sanitizeReservationResponse(original);

    expect(result).toEqual({
      body: { order_id: "order-id", status: "pending" },
      guestToken: "guest_secret",
      orderId: "order-id",
    });
    expect(original.guest_access_token).toBe("guest_secret");
  });

  it("uses isolated HttpOnly cookies with a bounded lifetime", () => {
    expect(guestOrderCookieName("order-id")).toBe("ticketing_guest_order_order-id");
    expect(guestSessionCookieName("demo_session_123")).toBe(
      "ticketing_guest_session_demo_session_123"
    );
    expect(guestCheckoutCookieOptions()).toMatchObject({
      httpOnly: true,
      sameSite: "lax",
      path: "/api",
      maxAge: GUEST_CHECKOUT_COOKIE_MAX_AGE_SECONDS,
    });
  });

  it("marks guest cookies as Secure in production", () => {
    vi.stubEnv("NODE_ENV", "production");

    expect(guestCheckoutCookieOptions().secure).toBe(true);
  });
});
