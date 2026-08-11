import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getAuthCookieName } from "@/lib/auth-cookie";

const PUBLIC_ROUTES = [
  "/login",
  "/auth/oidc/callback",
  "/platform/login",
  "/terms",
  "/privacy",
  "/cookies",
  "/legal/security",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/api/v1/")) {
    return NextResponse.next();
  }

  const token = request.cookies.get(getAuthCookieName())?.value;
  const isPublic = PUBLIC_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`));
  const isPlatformRoute = pathname === "/platform" || pathname.startsWith("/platform/");
  const isMarketingHome = pathname === "/" && !token;

  if (isMarketingHome) {
    return NextResponse.next();
  }

  if (isPlatformRoute) {
    if (!token && pathname !== "/platform/login" && !pathname.startsWith("/platform/login/")) {
      return NextResponse.redirect(new URL("/platform/login", request.url));
    }
    if (token && pathname === "/platform/login") {
      return NextResponse.redirect(new URL("/platform", request.url));
    }
    return NextResponse.next();
  }

  if (!token && !isPublic) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (token && pathname === "/login") {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
