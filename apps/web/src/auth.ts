import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    error?: "RefreshAccessTokenError";
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

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    idToken?: string;
    refreshToken?: string;
    expiresAt?: number;
    role?: string;
    error?: "RefreshAccessTokenError";
  }
}

/**
 * Renueva los tokens de Cognito contra el backend usando el refresh_token.
 * Cognito (REFRESH_TOKEN_AUTH) NO devuelve un refresh_token nuevo, así que
 * conservamos el que ya tenemos. Si el refresh falla (refresh_token revocado
 * o expirado), marcamos el token con un error para forzar re-login.
 */
async function refreshTokens(token: import("next-auth/jwt").JWT) {
  const apiUrl = process.env.API_URL ?? "http://localhost:8000";
  try {
    if (!token.refreshToken) throw new Error("missing_refresh_token");

    const res = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    });
    if (!res.ok) throw new Error("refresh_failed");

    const tokens = (await res.json()) as {
      access_token: string;
      id_token: string;
      expires_in: number;
    };

    return {
      ...token,
      accessToken: tokens.access_token,
      idToken: tokens.id_token,
      expiresAt: Date.now() + tokens.expires_in * 1000,
      error: undefined,
    };
  } catch {
    return { ...token, error: "RefreshAccessTokenError" as const };
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  // Trust the host of the incoming request (works behind ngrok, vercel preview,
  // reverse proxies). Auth.js then derives the callback URL from req.nextUrl
  // instead of hardcoding AUTH_URL.
  trustHost: true,
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
      // Si el refresh del token falló, la sesión ya no sirve: forzamos login.
      if (!isLoggedIn || auth?.error === "RefreshAccessTokenError") {
        const loginUrl = new URL("/login", request.nextUrl);
        loginUrl.searchParams.set("callbackUrl", path);
        return Response.redirect(loginUrl);
      }
      return true;
    },
    async jwt({ token, user }) {
      // Login inicial: persistimos los tokens recién emitidos.
      if (user) {
        token.accessToken = user.accessToken;
        token.idToken = user.idToken;
        token.refreshToken = user.refreshToken;
        token.expiresAt = user.expiresAt;
        token.role = user.role;
        return token;
      }

      // Token aún válido (con 60s de margen para evitar carreras de reloj).
      if (token.expiresAt && Date.now() < token.expiresAt - 60_000) {
        return token;
      }

      // Token expirado o por expirar: lo renovamos contra el backend.
      return refreshTokens(token);
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.idToken = token.idToken;
      session.error = token.error;
      if (session.user) {
        session.user.role = token.role;
      }
      return session;
    },
  },
});
