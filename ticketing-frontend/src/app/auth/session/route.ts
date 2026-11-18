import { NextResponse } from "next/server";

import {
  getAccessTokenExpiration,
  SESSION_COOKIE,
  validateAccessToken,
} from "@/auth/session";

export async function POST(request: Request) {
  const authorization = request.headers.get("authorization");
  const accessToken = authorization?.startsWith("Bearer ")
    ? authorization.slice("Bearer ".length)
    : null;

  if (!accessToken || !(await validateAccessToken(accessToken))) {
    const response = NextResponse.json({ detail: "Invalid session" }, { status: 401 });
    response.cookies.delete(SESSION_COOKIE);
    return response;
  }

  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(SESSION_COOKIE, accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    expires: getAccessTokenExpiration(accessToken) ?? undefined,
  });
  return response;
}

export function DELETE() {
  const response = new NextResponse(null, { status: 204 });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
