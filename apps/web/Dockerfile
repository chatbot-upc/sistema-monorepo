# Dockerfile de Next.js (panel admin) — multi-stage, output standalone.
# IMPORTANTE: el contexto de build es la RAIZ del monorepo (no apps/web),
# porque usa pnpm workspaces y el lockfile vive en la raiz.
#   docker build -f apps/web/Dockerfile -t web .
# Compatible con ARM (Graviton) y x86: node:22-alpine es multi-arch.

FROM node:22-alpine AS base
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate
WORKDIR /app

# ---- deps: instala con el lockfile (cacheable) ----
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile --filter web...

# ---- build: compila Next en modo standalone ----
FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web ./apps/web
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter web build

# ---- runtime: imagen minima solo con el server standalone ----
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
# El standalone incluye la estructura del monorepo (apps/web/server.js)
COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /app/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
