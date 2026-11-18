import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  classifyGuestCheckoutRoute,
  guestCheckoutCookieOptions,
  guestOrderCookieName,
  guestSessionCookieName,
  sanitizeReservationResponse,
} from "@/auth/guestCheckout";
import { SESSION_COOKIE } from "@/auth/session";
import {
  getValidationStationCookieHeader,
  VALIDATION_STATION_COOKIE,
} from "@/auth/validationStationSession";

const backendApiUrl = (process.env.BACKEND_API_URL || "http://localhost:8000").replace(
  /\/$/,
  ""
);

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxyApiRequest(request: Request, context: RouteContext): Promise<Response> {
  const { path } = await context.params;
  const requestUrl = new URL(request.url);
  const upstreamUrl = `${backendApiUrl}/${path.map(encodeURIComponent).join("/")}${requestUrl.search}`;
  const requestHeaders = new Headers(request.headers);
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(SESSION_COOKIE)?.value;
  const validationStationCookie = getValidationStationCookieHeader(
    path,
    cookieStore.get(VALIDATION_STATION_COOKIE)?.value
  );
  const guestRoute = classifyGuestCheckoutRoute(path, request.method);
  const proxyClientIp = request.headers.get("x-real-ip");
  let guestToken: string | undefined;

  if (guestRoute?.kind === "demo-checkout" || guestRoute?.kind === "checkout-summary" || guestRoute?.kind === "tickets-pdf") {
    guestToken = cookieStore.get(guestOrderCookieName(guestRoute.orderId))?.value;
  } else if (guestRoute?.kind === "demo-confirmation") {
    guestToken = cookieStore.get(guestSessionCookieName(guestRoute.sessionId))?.value;
  }

  requestHeaders.delete("host");
  requestHeaders.delete("content-length");
  requestHeaders.delete("cookie");
  requestHeaders.delete("expect");
  requestHeaders.delete("x-ticketing-client-ip");
  requestHeaders.delete("x-guest-token");
  if (proxyClientIp) {
    requestHeaders.set("x-ticketing-client-ip", proxyClientIp);
  }
  if (accessToken) {
    requestHeaders.set("authorization", `Bearer ${accessToken}`);
  }
  if (validationStationCookie) {
    requestHeaders.set("cookie", validationStationCookie);
  }
  if (guestToken) {
    requestHeaders.set("x-guest-token", guestToken);
  }

  const hasBody = request.method !== "GET" && request.method !== "HEAD";

  try {
    const requestInit: RequestInit = {
      method: request.method,
      headers: requestHeaders,
      cache: "no-store",
      redirect: "manual",
    };
    if (hasBody) {
      requestInit.body = await request.arrayBuffer();
    }

    const upstreamResponse = await fetch(upstreamUrl, requestInit);
    const responseHeaders = new Headers(upstreamResponse.headers);
    responseHeaders.delete("content-length");
    responseHeaders.delete("content-encoding");

    if (guestRoute?.kind === "reservation" && upstreamResponse.ok) {
      const reservation = sanitizeReservationResponse(await upstreamResponse.json());
      const response = NextResponse.json(reservation.body, {
        status: upstreamResponse.status,
        headers: responseHeaders,
      });

      if (reservation.guestToken && reservation.orderId) {
        response.cookies.set(
          guestOrderCookieName(reservation.orderId),
          reservation.guestToken,
          guestCheckoutCookieOptions()
        );
      }

      return response;
    }

    if (guestRoute?.kind === "demo-checkout" && guestToken && upstreamResponse.ok) {
      const body: unknown = await upstreamResponse.json();
      const response = NextResponse.json(body, {
        status: upstreamResponse.status,
        headers: responseHeaders,
      });
      const sessionId =
        body && typeof body === "object" && !Array.isArray(body)
          ? (body as Record<string, unknown>).checkout_session_id
          : null;

      if (typeof sessionId === "string") {
        response.cookies.set(
          guestSessionCookieName(sessionId),
          guestToken,
          guestCheckoutCookieOptions()
        );
      }

      return response;
    }

    return new NextResponse(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("API proxy request failed", error);
    return Response.json(
      { detail: "El servicio no está disponible temporalmente" },
      { status: 502 }
    );
  }
}

export const GET = proxyApiRequest;
export const POST = proxyApiRequest;
export const PUT = proxyApiRequest;
export const PATCH = proxyApiRequest;
export const DELETE = proxyApiRequest;
