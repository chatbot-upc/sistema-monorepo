# Web — Admin CRM

Next.js 16 + React 19 + Tailwind v4. Panel administrativo del chatbot UPC.

## Setup

Desde la raíz del monorepo:

```bash
pnpm install
pnpm dev:web
```

Abre http://localhost:3000

## Estructura

```
src/
├── app/
│   ├── (app)/         Rutas autenticadas: dashboard, conversations, documents, intents, reports
│   └── login/         Login (Cognito)
├── components/        UI compartida (charts, conversations, dashboard, shell, ui)
└── lib/               Utilidades
```

## Comandos

```bash
pnpm dev:web      # dev server (puerto 3000)
pnpm build:web    # production build
pnpm lint:web     # ESLint
```

## Stack

- Next.js 16 (App Router)
- React 19
- Tailwind v4 (con `@theme` mapeado a tokens del diseño Pencil)
- shadcn/ui + Lucide icons
- AWS Amplify Auth (Cognito) — pendiente Fase 5
