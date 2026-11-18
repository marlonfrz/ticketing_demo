const SAFE_COOKIE_SEGMENT = /^[A-Za-z0-9_-]{1,255}$/;

export const GUEST_CHECKOUT_COOKIE_MAX_AGE_SECONDS = 24 * 60 * 60;

export type GuestCheckoutRoute =
  | { kind: "reservation" }
  | { kind: "demo-checkout"; orderId: string }
  | { kind: "checkout-summary"; orderId: string }
  | { kind: "tickets-pdf"; orderId: string }
  | { kind: "demo-confirmation"; sessionId: string }
  | null;

export type SanitizedReservationResponse = {
  body: unknown;
  guestToken: string | null;
  orderId: string | null;
};

function isSafeCookieSegment(value: string | undefined): value is string {
  return Boolean(value && SAFE_COOKIE_SEGMENT.test(value));
}

export function guestOrderCookieName(orderId: string): string {
  return `ticketing_guest_order_${orderId}`;
}

export function guestSessionCookieName(sessionId: string): string {
  return `ticketing_guest_session_${sessionId}`;
}

export function guestCheckoutCookieOptions() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/api",
    maxAge: GUEST_CHECKOUT_COOKIE_MAX_AGE_SECONDS,
  };
}

export function classifyGuestCheckoutRoute(
  path: string[],
  method: string
): GuestCheckoutRoute {
  if (
    method === "POST" &&
    path.length === 4 &&
    path[0] === "events" &&
    path[2] === "reservations" &&
    path[3] === "with-order"
  ) {
    return { kind: "reservation" };
  }

  const orderId = path[3];
  if (
    method === "POST" &&
    path.length === 4 &&
    path[0] === "payments" &&
    path[1] === "demo" &&
    path[2] === "checkout" &&
    isSafeCookieSegment(orderId)
  ) {
    return { kind: "demo-checkout", orderId };
  }

  const summaryOrderId = path[1];
  if (
    method === "GET" &&
    path.length === 3 &&
    path[0] === "orders" &&
    path[2] === "checkout-summary" &&
    isSafeCookieSegment(summaryOrderId)
  ) {
    return { kind: "checkout-summary", orderId: summaryOrderId };
  }

  const pdfOrderId = path[2];
  if (
    method === "GET" &&
    path.length === 4 &&
    path[0] === "tickets" &&
    path[1] === "order" &&
    path[3] === "pdf" &&
    isSafeCookieSegment(pdfOrderId)
  ) {
    return { kind: "tickets-pdf", orderId: pdfOrderId };
  }

  const sessionId = path[3];
  if (
    method === "POST" &&
    path.length === 4 &&
    path[0] === "payments" &&
    path[1] === "demo" &&
    path[2] === "confirm-session" &&
    isSafeCookieSegment(sessionId)
  ) {
    return { kind: "demo-confirmation", sessionId };
  }

  return null;
}

export function sanitizeReservationResponse(body: unknown): SanitizedReservationResponse {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return { body, guestToken: null, orderId: null };
  }

  const sanitizedBody = { ...(body as Record<string, unknown>) };
  const guestToken =
    typeof sanitizedBody.guest_access_token === "string"
      ? sanitizedBody.guest_access_token
      : null;
  const orderId =
    typeof sanitizedBody.order_id === "string" &&
    isSafeCookieSegment(sanitizedBody.order_id)
      ? sanitizedBody.order_id
      : null;

  delete sanitizedBody.guest_access_token;

  return { body: sanitizedBody, guestToken, orderId };
}
