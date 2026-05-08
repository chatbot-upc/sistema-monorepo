import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    user: {
      role?: string;
    } & DefaultSession["user"];
  }
  interface User {
    accessToken?: string;
    idToken?: string;
    refreshToken?: string;
    expiresAt?: number;
    role?: string;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      name: "UPC Cognito",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(raw) {
        const email = typeof raw?.email === "string" ? raw.email : "";
        const password = typeof raw?.password === "string" ? raw.password : "";
        if (!email || !password) return null;

        const apiUrl = process.env.API_URL ?? "http://localhost:8000";

        const loginRes = await fetch(`${apiUrl}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (!loginRes.ok) return null;

        const tokens = (await loginRes.json()) as {
          access_token: string;
          id_token: string;
          refresh_token: string;
          expires_in: number;
        };

        const meRes = await fetch(`${apiUrl}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${tokens.id_token}` },
        });
        if (!meRes.ok) return null;

        const me = (await meRes.json()) as {
          id: number;
          email: string;
          name: string;
          role: string;
        };

        return {
          id: String(me.id),
          email: me.email,
          name: me.name,
          role: me.role,
          accessToken: tokens.access_token,
          idToken: tokens.id_token,
          refreshToken: tokens.refresh_token,
          expiresAt: Date.now() + tokens.expires_in * 1000,
        };
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  session: { strategy: "jwt" },
  callbacks: {
    authorized({ request, auth }) {
      const isLoggedIn = Boolean(auth);
      const path = request.nextUrl.pathname;
      const publicPaths = ["/login", "/api/auth"];
      const isPublic = publicPaths.some((p) => path.startsWith(p));
      if (isPublic) return true;
      if (!isLoggedIn) {
        const loginUrl = new URL("/login", request.nextUrl);
        loginUrl.searchParams.set("callbackUrl", path);
        return Response.redirect(loginUrl);
      }
      return true;
    },
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.idToken = user.idToken;
        token.refreshToken = user.refreshToken;
        token.expiresAt = user.expiresAt;
        token.role = user.role;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string | undefined;
      session.idToken = token.idToken as string | undefined;
      if (session.user) {
        session.user.role = token.role as string | undefined;
      }
      return session;
    },
  },
});
