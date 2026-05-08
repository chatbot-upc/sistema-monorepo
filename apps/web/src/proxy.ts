import { auth } from "@/auth";

export default auth;

export const config = {
  matcher: [
    "/((?!api/auth|login|_next/static|_next/image|favicon.ico|.*\\..*).*)",
  ],
};
