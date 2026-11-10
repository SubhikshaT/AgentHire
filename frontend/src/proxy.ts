import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

// Optimistic check only: redirect to /login when there is no auth cookie.
// The backend validates the token and role on every API call.
const COOKIE = "agenthire_token";

export function proxy(request: NextRequest) {
  if (!request.cookies.get(COOKIE)) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/jobs/:path*",
    "/candidates/:path*",
    "/resumes/:path*",
    "/interviews/:path*",
    "/reports/:path*",
    "/settings/:path*",
    "/analytics/:path*",
    "/candidate/:path*",
  ],
};
