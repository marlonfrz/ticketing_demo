import { NextResponse, type NextRequest } from "next/server";
import { isProtectedPath } from "./auth/protectedRoutes";
import { getAccessTokenExpiration, SESSION_COOKIE } from "./auth/session";

export async function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (!isProtectedPath(pathname)) {
    return NextResponse.next();
  }

  const accessToken = request.cookies.get(SESSION_COOKIE)?.value;
  if (accessToken && getAccessTokenExpiration(accessToken)) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", `${pathname}${search}`);
  const response = NextResponse.redirect(loginUrl);
  response.cookies.delete(SESSION_COOKIE);
  return response;
}

export const config = {
  matcher: [
    "/profile/:path*",
    "/my-tickets/:path*",
    "/promoter/:path*",
    "/admin/:path*",
    "/validation-stations/:path*",
    "/events/:eventId/manage",
  ],
};
