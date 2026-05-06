# Tokens — Chatbot UPC Admin

Fuente de verdad: `design/chatbot-admin.pen`. Estos tokens están sincronizados con las variables del archivo Pencil. **No agregar tokens nuevos sin justificarlo contra los existentes.**

---

## Color

### Superficies y fondos

| Token | Valor | Variable CSS | Tailwind | Uso |
|---|---|---|---|---|
| `bg` | `#FCFCFB` | `--bg` | `bg-bg` | Fondo global. Off-white cálido casi imperceptible — quita el filo clínico. |
| `surface` | `#FFFFFF` | `--surface` | `bg-surface` | Tarjetas, modales, dropdowns sobre `bg`. |
| `surface-2` | `#F7F6F3` | `--surface-2` | `bg-surface-2` | Filas alternas, hover sutil, headers de columnas, inputs. |

### Texto (Zinc + Stone)

| Token | Valor | Variable CSS | Tailwind | Uso |
|---|---|---|---|---|
| `fg` | `#18181B` | `--fg` | `text-fg` | Texto principal — Zinc 900, negro con cast azulado. |
| `fg-2` | `#44403C` | `--fg-2` | `text-fg-2` | Texto secundario, body largo — Stone 700. |
| `muted` | `#78716C` | `--muted` | `text-muted` | Metadata mono (timestamps, IDs), labels — Stone 500. |
| `muted-2` | `#A8A29E` | `--muted-2` | `text-muted-2` | Placeholders, texto deshabilitado — Stone 400. |

### Acentos y acción

| Token | Valor | Variable CSS | Tailwind | Uso |
|---|---|---|---|---|
| `accent` | `#18181B` | `--accent` | `bg-accent` / `text-accent` | Botón primario. Mismo valor que `fg` para coherencia. |
| `accent-fg` | `#FFFFFF` | `--accent-fg` | `text-accent-fg` | Texto sobre `accent`. |

### Bordes y separadores

| Token | Valor | Variable CSS | Tailwind | Uso |
|---|---|---|---|---|
| `line` | `#E7E5E4` | `--line` | `border-line` | Borde por defecto — Stone 200. |
| `line-2` | `#D6D3D1` | `--line-2` | `border-line-2` | Borde de énfasis: hover de inputs, divisores fuertes — Stone 300. |

### Estado / señal — terracota peruano

| Token | Valor | Variable CSS | Tailwind | Uso |
|---|---|---|---|---|
| `signal` | `#B5411C` | `--signal` | `text-signal` / `bg-signal` | **EXCLUSIVO**: estado `escalated`, errores, "necesita atención humana", baja confianza SBERT. Terracota serio, no naranja Sentry. |
| `signal-soft` | `#FBF1EC` | `--signal-soft` | `bg-signal-soft` | Fondo de fila escalada, badge background, toast error. |
| `success` | `#15803D` | `--success` | `text-success` / `bg-success` | Estado `closed`, métricas positivas, confirmaciones. |
| `success-soft` | `#F0FDF4` | `--success-soft` | `bg-success-soft` | Fondo de badge `closed`, toast de éxito. |

### UPC institucional — uso muy restringido

| Token | Valor | Variable CSS | Tailwind | Uso |
|---|---|---|---|---|
| `upc` | `#A01E2D` | `--upc` | `text-upc` / `bg-upc` | **SOLO** focus ring, links (`a.link`), barra del item activo del sidebar, logo de la app, énfasis del welcome heading. |
| `upc-soft` | `#FBEEF0` | `--upc-soft` | `bg-upc-soft` | Halo del focus ring en inputs (`box-shadow: 0 0 0 3px var(--upc-soft)`). |

> Los colores no-neutros (`signal`, `success`, `upc`) son **escasos por diseño**. Si dudas si aplica, no lo uses. Cada uno tiene un significado fijo y no es intercambiable.

---

## Tipografía

### Familias

| Token | Familia | Variable CSS | Tailwind | Uso |
|---|---|---|---|---|
| `font-sans` | Inter | `--font-sans` | `font-sans` | UI, body, headings, buttons. Default global. |
| `font-mono` | JetBrains Mono | `--font-mono` | `font-mono` | Números, timestamps, conv_id, teléfonos, scores, latencias, intent labels. |
| `font-serif` | Newsreader | `--font-serif` | `font-serif` | **3 usos consistentes**: (1) número hero del dashboard (HU31), (2) page title de pantallas principales (`text-3xl`), (3) brand mark del sidebar (logo + nombre app). Nada más. |

Cargar vía `next/font/google` con `display: 'swap'` y subset latino.

### Escala de tamaño

| Token | Valor | Tailwind | Line-height | Uso |
|---|---|---|---|---|
| `text-2xs` | 10px | `text-2xs` | 1.4 | Labels mono uppercase en stat cards, tags pequeños. |
| `text-xs` | 11px | `text-xs` | 1.4 | Metadata mono, captions. |
| `text-sm` | 12.5px | `text-sm` | 1.5 | Body secundario, helper text de inputs, timestamps. |
| `text-base` | 14px | `text-base` | 1.5 | Body principal, button label, input value. **Default**. |
| `text-md` | 15px | `text-md` | 1.5 | Body en chat bubbles, énfasis ligero. |
| `text-lg` | 18px | `text-lg` | 1.4 | Títulos de card, nombres en lista de conversaciones. |
| `text-xl` | 22px | `text-xl` | 1.3 | Section headings (h3). |
| `text-2xl` | 28px | `text-2xl` | 1.2 | Page headings (h2), título de pantalla. |
| `text-3xl` | 36px | `text-3xl` | 1.15 | Page heading enfatizado, números secundarios de stats. |
| `text-display` | 84px | `text-display` | 0.95 | Newsreader. Número hero del dashboard. |

### Tracking (letter-spacing)

- `≥18px`: `-0.2px` a `-0.4px` (apretado, modo Vercel/Linear).
- `<18px`: `0px` (default Inter).
- Mono labels uppercase: `0.4px` a `0.6px`.

### Pesos

- Inter: `400` (body), `500` (énfasis y buttons), `600` (headings), `700` (números secundarios). Nunca `800`+.
- JetBrains Mono: `400` exclusivamente.
- Newsreader: `500` con `font-variation-settings: 'opsz' 72`.

---

## Espaciado

Base 4px. Solo usar tokens — nada de `padding: 13px`.

| Token | Valor | Tailwind | Uso típico |
|---|---|---|---|
| `space-1` | 4px | `p-1` / `gap-1` | Gap entre icon y label, gap interno de pills. |
| `space-2` | 8px | `p-2` / `gap-2` | Padding vertical de pills, gap entre meta items. |
| `space-3` | 12px | `p-3` / `gap-3` | Padding de buttons sm, gap en form fields. |
| `space-4` | 16px | `p-4` / `gap-4` | Padding default de card, gap entre filas. |
| `space-5` | 20px | `p-5` / `gap-5` | Padding de card md. |
| `space-6` | 24px | `p-6` / `gap-6` | Padding de card lg, gap entre secciones. |
| `space-8` | 32px | `p-8` / `gap-8` | Padding de page container, gap entre bloques mayores. |
| `space-10` | 40px | `p-10` / `gap-10` | Margen superior de hero. |
| `space-12` | 48px | `p-12` / `gap-12` | Padding de empty states. |

---

## Border radius

| Token | Valor | Tailwind | Uso |
|---|---|---|---|
| `radius-xs` | 2px | `rounded-xs` | Pills mono, tags. |
| `radius-sm` | 4px | `rounded-sm` | Inputs, buttons sm, chips. |
| `radius-md` | 6px | `rounded-md` | Buttons default, badges. |
| `radius-lg` | 8px | `rounded-lg` | Cards, modales, dropdowns. |
| `radius-xl` | 12px | `rounded-xl` | Cards de hero, contenedores grandes. |

> Nada de `rounded-full` excepto avatares circulares.

---

## Sombras

Minimalistas. Solo para overlays — nunca para cards estáticas (esas usan `border-line`).

| Token | Valor | Tailwind | Uso |
|---|---|---|---|
| `shadow-overlay` | `0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.08)` | `shadow-overlay` | Dropdowns, popovers. |
| `shadow-modal` | `0 10px 40px rgba(0,0,0,0.12)` | `shadow-modal` | Dialogs, command palette. |
| `shadow-toast` | `0 4px 16px rgba(0,0,0,0.10)` | `shadow-toast` | Toasts. |

---

## Z-index

| Token | Valor | Uso |
|---|---|---|
| `z-base` | 0 | Default. |
| `z-sticky` | 10 | Topbar, table header sticky. |
| `z-dropdown` | 30 | Dropdowns, popovers. |
| `z-overlay` | 40 | Backdrop de modales. |
| `z-modal` | 50 | Dialog content. |
| `z-toast` | 60 | Toasts (sobre modales). |

---

## Breakpoints

CRM admin = principalmente desktop. No pretender mobile-first.

| Token | Valor | Tailwind | Uso |
|---|---|---|---|
| `sm` | 640px | `sm:` | Tablet vertical (read-only). |
| `md` | 768px | `md:` | Tablet horizontal — punto mínimo soportado. |
| `lg` | 1024px | `lg:` | Desktop pequeño — sidebar visible. |
| `xl` | 1280px | `xl:` | Desktop estándar — diseño objetivo. |
| `2xl` | 1536px | `2xl:` | Pantalla grande — limita ancho de contenido a 1440px. |

> Ancho mínimo soportado del panel: 1024px. Por debajo, mostrar mensaje "El CRM está optimizado para pantallas de 1024px o más".

---

## Focus ring — UPC institucional

```css
outline: 2px solid var(--upc);
outline-offset: 2px;
border-radius: inherit;
```

Aplicar a todo elemento interactivo en `:focus-visible`. **Nunca** ocultar el focus. El rojo UPC aquí es el guiño institucional al producto — único color de marca en toda la app.

Para inputs, además del outline el focus muestra un halo:
```css
.input:focus { border-color: var(--upc); box-shadow: 0 0 0 3px var(--upc-soft); }
```

---

## Iconos

- Librería única: **Lucide React**.
- Tamaños: `14px` (inline en text-sm), `16px` (default UI), `20px` (sidebar nav, buttons lg), `24px` (empty states).
- Stroke width: `1.75` global. `2` solo para iconos de acción primaria.
- Color: hereda `currentColor` del texto.

---

## Tabla resumen — qué no inventar

- No agregar más colores neutros (ya hay 7).
- No agregar gradientes.
- No agregar dark mode (fuera de alcance).
- No agregar otra fuente serif.
- No agregar tamaños de texto entre los definidos (no `13px`, no `26px`).
- No agregar shadows decorativas.
