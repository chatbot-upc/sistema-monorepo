# Components — Chatbot UPC Admin

Especificación de los 14 componentes del CRM. Cada uno: anatomía, variantes, tamaños, estados, reglas. Implementación sugerida sobre **shadcn/ui** + Tailwind con los tokens de `tokens.md`.

> Convención: las clases mostradas son del config Tailwind de este proyecto (no del default). Por ejemplo `text-sm` = 12.5px, no 14px.

---

## 1. Button

### Anatomía

`[icon-left?] [label] [icon-right?]` · padding horizontal > vertical · `radius-md` · `font-medium`.

### Variantes

| Variante | Background | Text | Border | Uso |
|---|---|---|---|---|
| `primary` | `accent` (#0A0A0A) | `accent-fg` | none | Acción principal de la pantalla. Una sola por contexto. |
| `secondary` | `surface` | `fg` | `1px line` → hover `line-2` | Acciones secundarias. |
| `ghost` | transparent | `fg-2` | none → hover `bg-surface-2` | Acciones terciarias, toolbar items. |
| `destructive` | `surface` | `signal` | `1px signal/30` → hover `signal-soft` | Eliminar, cerrar conversación, descartar. **Nunca** primary rojo. |

### Tamaños

| Size | Height | Padding-x | Font | Icon size | Uso |
|---|---|---|---|---|---|
| `sm` | 28px | `space-3` (12) | `text-sm` (12.5) | 14px | Toolbar de tabla, acciones inline. |
| `md` | 36px | `space-4` (16) | `text-base` (14) | 16px | Default. |
| `lg` | 44px | `space-5` (20) | `text-base` (14) | 20px | Forms, login submit. |

Gap interno entre icon y label: `space-2` (8px).

### Estados

- `default` → variante base.
- `hover` → ver tabla (cambio sutil de border o bg).
- `active` (pressed) → `opacity: 0.9`.
- `disabled` → `opacity: 0.4`, `cursor: not-allowed`, sin hover.
- `loading` → spinner Lucide `Loader2` animado, texto sigue visible, click bloqueado.
- `focus-visible` → ring 2px `accent` offset 2px (heredado de globals).

### Antipatrones

- ❌ Botón primary azul. → ✅ Negro `accent`.
- ❌ Más de un primary visible al mismo tiempo en una pantalla.
- ❌ Iconos rellenos. → ✅ Solo Lucide outline.

---

## 2. Input · Textarea · Select

### Anatomía

```
Label (opcional)        [hint inline derecho opcional]
[icon-left?] [field] [icon-right? · clear · chevron]
Helper text  /  Error message
```

### Especificación visual

- Container: `radius-sm`, `bg-surface-2`, `border 1px line`.
- Hover: `border-line-2`.
- Focus: `border-accent`, ring 2px `accent` offset 2px.
- Error: `border-signal`, helper text en `text-signal`.
- Disabled: `bg-surface-2`, `text-muted-2`, sin hover.

### Tamaños

| Size | Height | Font |
|---|---|---|
| `sm` | 32px | `text-sm` |
| `md` | 40px | `text-base` |
| `lg` | 48px | `text-base` |

### Reglas de tipo

- Inputs numéricos (teléfono, score): `font-mono` con `tabular-nums`.
- Search input: icon `Search` izquierda, `Cmd+K` shortcut hint derecha en `text-2xs muted`.
- Textarea: min-height 96px, max-height 240px con scroll, `resize: none` si no aplica.
- Select: usar shadcn `Select` (Radix) con dropdown que hereda `shadow-overlay`.

### Label y helper

- Label: `text-sm font-medium text-fg-2` arriba del input, `space-2` de gap.
- Helper / error: `text-xs muted` (helper) o `text-xs signal` (error), `space-1` de gap inferior.
- Required marker: asterisco `text-signal` después del label.

---

## 3. Pill / Badge

### Variantes de status

Las únicas relevantes para el dominio son los estados de conversación + intent confidence.

| Variante | Background | Text | Border | Uso |
|---|---|---|---|---|
| `active` | `surface-2` | `fg-2` | `1px line` | Conversación en curso. |
| `escalated` | `signal-soft` | `signal` | `1px signal/30` | Necesita admin. **Único** uso del rojo. |
| `closed` | `success-soft` | `success` | `1px success/30` | Resuelta / cerrada. |
| `draft` | transparent | `muted` | `1px line dashed` | Documentos sin indexar, intenciones nuevas. |
| `neutral` | `surface-2` | `fg-2` | none | Tags genéricos, contadores. |

### Especificación visual

- Padding: `2px 8px` (sm) · `4px 10px` (md).
- Radius: `radius-xs` (2px) — pills son cuadradas, no redondeadas.
- Font: `font-mono text-2xs uppercase` con tracking `0.4px` para `active/escalated/closed/draft`.
- Font: `font-sans text-xs` sin uppercase para `neutral` (tags, contadores).

### Intent pill (caso especial)

Estructura: `[intent_name] [score]` separados por `space-1`.

```
fechas_pago 0.72   → font-mono text-xs · score en muted
fallback 0.41      → cuando score < 0.55, fondo signal-soft, texto signal
```

---

## 4. Card

### Anatomía

```
[Header? — title + acciones derecha]
[Divider line opcional]
[Body — contenido]
[Footer? — meta + acciones]
```

### Variantes

| Variante | Padding | Border | Background | Uso |
|---|---|---|---|---|
| `default` | `space-5` (20) | `1px line` | `surface` | Cards de stats, listas, contenido genérico. |
| `compact` | `space-4` (16) | `1px line` | `surface` | Cards en grids densos. |
| `flush` | 0 | `1px line` | `surface` | Card que contiene una tabla full-bleed. |
| `hero` | `space-8` (32) | none | `surface` | Hero del dashboard del día. |

### Especificación

- `radius-lg` (8px) excepto `hero` que usa `radius-xl` (12px).
- **Sin sombra**. La separación es por borde.
- Header: `text-lg font-semibold` + acciones `ghost sm` a la derecha justificadas con `space-between`.
- Divider entre header y body: `1px line`, full-width (cancela el padding del card).
- Hover sobre card clickeable: `border-line-2`. **No** elevar con shadow.

---

## 5. Table

### Anatomía

```
[Header row] sticky · bg-surface-2 · border-bottom line
[Body rows]  hover:bg-surface-2
[Pagination footer]
```

### Especificación

- Filas: alto 48-56px (md). En lista de conversaciones: 56px para acomodar avatar + 2 líneas.
- Header: `text-2xs font-mono uppercase text-muted` tracking `0.6px`. Padding vertical `space-3`.
- Celdas: `text-sm` body, padding `space-3 space-4`.
- Border separador entre filas: `1px line` solo bottom.
- Numeric / mono cells: `font-mono tabular-nums text-xs text-muted`.
- Sort indicator: `ChevronUp` / `ChevronDown` 14px en muted, en accent si activa.
- Selected row: `bg-surface-2` + barra izquierda 2px `accent`.
- **Fila escalada**: `bg-signal-soft` en toda la fila, mantener al hover. Texto sigue siendo `fg`.

### Empty state interno

Cuando no hay filas, mostrar Empty state (componente 11) dentro del cuerpo de la tabla con padding `space-12`.

### Pagination

- Mostrar solo si > 25 filas.
- `Previous` / `Next` como buttons `secondary sm` con icons.
- Indicador "página 3 de 12" en `text-sm muted` al centro.
- "20 por página" select `sm` a la derecha.

---

## 6. Sidebar nav

### Estructura

```
[Logo + nombre app]               · 56px alto · padding x space-4
[separator]
[Section label — DASHBOARDS]      · text-2xs mono uppercase muted
  [Nav item · icon · label]       · 36px alto · radius-sm
  [Nav item · activo]             · barra 2px accent izquierda · bg-surface-2
[Section label — GESTIÓN]
  ...
[Footer: avatar admin + email]    · sticky bottom
```

### Especificación

- Ancho fijo `240px`.
- `bg-surface`, `border-right 1px line`.
- Nav item:
  - Padding `space-2 space-3`.
  - Icon 16px en `muted`, label `text-sm fg-2`.
  - Hover: `bg-surface-2`.
  - Activo: `bg-surface-2`, label `text-fg font-medium`, icon `accent`, indicador izquierdo 2px `accent` height 60% centrado.
- Section labels: padding `space-3 space-3 space-1`.
- Footer admin: padding `space-3`, `border-top 1px line`. Avatar 32px circular con iniciales en `bg-accent text-accent-fg`.

### Items del backlog

```
DASHBOARDS
  · Inicio (HU31)              [Home]
  · Reportes (HU32)            [BarChart3]

CONVERSACIONES
  · Todas (HU27)               [MessageSquare]
  · Escaladas                  [AlertCircle · badge contador signal]

CONTENIDO
  · Documentos RAG (HU14-17)   [FileText]
  · Intenciones (HU09-13)      [Tags]

SISTEMA
  · Usuarios (futuro)          [Users] · disabled
```

---

## 7. Topbar

### Estructura

```
[Breadcrumb / page title]        [Search Cmd+K]    [Bell · contador]  [Avatar]
```

- Alto fijo `56px`.
- `bg-bg`, `border-bottom 1px line`, sticky top z-`sticky`.
- Padding `space-4 space-6`.
- Search: 320px ancho, input `md` con icon Search izq y `⌘K` chip derecho.
- Bell: button `ghost md`, badge superior derecho con contador en `bg-signal text-accent-fg text-2xs` cuando hay escaladas pendientes (Firebase push). Pulso suave 2s `box-shadow: 0 0 0 4px var(--signal-soft)` cuando llega notificación nueva.
- Avatar admin: 32px, click abre dropdown con `Cerrar sesión`.

---

## 8. Modal / Dialog

### Anatomía

```
[Backdrop · bg-black/40 · backdrop-blur-sm]
  [Dialog · centered]
    [Header: title + close]
    [Body]
    [Footer: cancel · confirm]
```

### Especificación

- Dialog: `bg-surface`, `radius-lg`, `shadow-modal`, max-width según tamaño:
  - `sm`: 400px (confirmaciones)
  - `md`: 560px (forms cortos)
  - `lg`: 720px (forms largos, upload de documentos)
- Header: `text-xl font-semibold`, padding `space-6`, button close ghost sm en esquina.
- Body: padding `space-6`, gap `space-4`.
- Footer: padding `space-4 space-6`, `border-top 1px line`, botones alineados a la derecha con `space-3` entre ellos. Cancel `secondary md`, primary action `primary md`.
- Backdrop: `bg-black/40 backdrop-blur-sm`.
- Animación: backdrop fade 180ms, dialog slide-up + fade 240ms `out-quart`.
- Cierre: backdrop click, Esc, button close.

---

## 9. Toast

### Anatomía

`[icon] [message] [action? · close]`

### Variantes

| Variante | Icon | Bg | Border | Text |
|---|---|---|---|---|
| `info` | `Info` | `surface` | `line` | `fg` |
| `success` | `CheckCircle2` | `success-soft` | `success/30` | `fg` |
| `error` | `AlertCircle` | `signal-soft` | `signal/30` | `fg` |

### Especificación

- Posición: bottom-right, `space-6` de margen.
- Width: 360-440px.
- Padding: `space-4`.
- `radius-lg`, `shadow-toast`.
- Icon 18px en color de variante.
- Auto-dismiss 5s (info/success), 8s (error). Persiste con hover.
- Stack: máximo 3 visibles, FIFO.

---

## 10. Stat card

### Estructura

```
[Label mono uppercase]       [Trend chip? +12%]
[Number · grande]
[Sublabel? · contexto]
```

### Especificación

- Padding `space-5`.
- Label: `text-2xs font-mono uppercase text-muted` tracking `0.5px`.
- Number: `text-3xl font-semibold tabular-nums fg`.
- Trend: chip `text-xs font-medium` con flecha pequeña, verde `success` o gris `muted`.
- Sublabel: `text-xs muted`.

### Caso especial — Hero del Dashboard (HU31)

```
[ETIQUETA MONO]
[Número en Newsreader serif text-display 84px]
[Sublabel mono · "+12 vs ayer"]
```

- Newsreader 500 con `font-variation-settings: 'opsz' 72`.
- Único lugar serif de toda la app.
- Trend en `text-sm font-mono success`.

---

## 11. Conversation row (lista de conversaciones)

### Estructura

```
[Avatar 36px · iniciales]  [Nombre · text-base font-medium]      [Time · mono xs]
                            [Phone · mono xs muted]               [Pill estado]
                            [Preview · text-sm fg-2 truncate]
```

- Layout: grid 2 columnas — left (avatar 36 + space-3) · middle (1fr) · right (auto).
- Alto: 72px con padding `space-3 space-4`.
- Border-bottom `1px line`.
- Hover: `bg-surface-2`, cursor pointer.
- Activa (seleccionada): `bg-surface-2` + barra 2px `accent` izquierda.
- **Escalada**: fila con `bg-signal-soft`, persiste en hover (apenas más oscuro). Pill escalated visible.

---

## 12. Chat bubble (hilo de conversación)

### Variantes

| Variante | Alineación | Background | Text | Radius |
|---|---|---|---|---|
| `student` | izquierda | `surface-2` | `fg` | `lg` con `xs` esquina inf-izq |
| `bot` | izquierda | `surface` `1px line` | `fg-2` | `lg` con `xs` esquina inf-izq |
| `admin` | derecha | `accent` | `accent-fg` | `lg` con `xs` esquina inf-der |

### Especificación

- Max-width: 60% del contenedor del thread.
- Padding `space-3 space-4`.
- Font: `text-md` (15px) line-height 1.5.
- Footer meta debajo del bubble:
  - `font-mono text-2xs muted`
  - Estructura: `[hora] · [intent_name confidence]` para student, `[bot · hora · latency]` para bot, `[admin · hora]` para admin.
  - Confidence `< 0.55` en `text-signal`.
- Gap entre bubbles: `space-3`. Entre bubbles del mismo autor consecutivos: `space-1`.

### Notice divider (sistema)

Texto centrado `font-mono text-2xs uppercase muted` con `border-top` y `border-bottom 1px line`, padding `space-2 0`. Ej: `"María Paula tomó el control · 09:18"`.

### Reply input area

Sticky bottom del thread, `border-top 1px line`, padding `space-4`. Textarea autosize + button primary `lg` "Enviar". Shortcut: `Cmd+Enter` para enviar.

---

## 13. Empty state

### Anatomía

```
[Icon 24px · muted en circle 56px bg-surface-2]
[Title · text-lg font-semibold]
[Description · text-sm muted · max-w-prose · centered]
[CTA primary md? opcional]
```

- Centrado, padding `space-12`.
- Gap vertical entre elementos: `space-3` (icon→title), `space-2` (title→desc), `space-5` (desc→CTA).
- No usar ilustraciones decorativas. Solo Lucide icon en círculo.

### Mensajes contextuales

| Pantalla | Icon | Title | Description |
|---|---|---|---|
| Lista vacía | `MessageSquare` | "Sin conversaciones aún" | "Cuando un estudiante escriba al WhatsApp aparecerá aquí." |
| Sin escaladas | `CheckCircle2` | "Todo bajo control" | "No hay conversaciones que necesiten tu atención." |
| Sin documentos | `FileText` | "Aún no hay documentos" | "Sube PDFs para que el chatbot los use como contexto." + CTA "Subir documento". |
| Búsqueda vacía | `SearchX` | "Sin resultados" | "Intenta con otro término o limpia los filtros." |

---

## 14. Conversation thread layout (compuesto)

Composición de Topbar + lista (col 1) + thread (col 2) usado en HU27/28/29. Ver `patterns.md` para el grid completo.

---

## Componentes auxiliares (no especificados en detalle)

Estos derivan de los anteriores con composición simple — usar shadcn defaults adaptados con los tokens:

- **Tooltip**: `bg-fg text-bg text-xs`, `radius-sm`, padding `space-1 space-2`. Delay 400ms.
- **Dropdown menu**: lista de items con icon + label + shortcut, `shadow-overlay`, `radius-lg`.
- **Tabs**: underline tabs con `border-bottom 2px accent` en activa, label `text-sm font-medium`.
- **Switch**: 32x18, `bg-line` off → `bg-accent` on. Sin animación bouncy.
- **Checkbox**: 16x16, `radius-xs`, `border line` → `bg-accent` checked con icon Check 12px `accent-fg`.
- **Radio group**: igual que checkbox pero círculo. Mantener radio solo si la opción es excluyente y son 2-4 opciones; si más, usar select.
- **Skeleton**: `bg-surface-2` con animación pulse 1.5s, mismo radius que el componente que reemplaza.
- **Avatar**: 24/32/40/56px circular. Iniciales `font-medium fg` sobre `bg-surface-2 border line`. Para admin: `bg-accent text-accent-fg`.
- **Divider**: `1px line`, márgenes según contexto.
- **Breadcrumb**: items `text-sm muted` con separador `/` o `ChevronRight 14px`. Último item `text-fg font-medium`.
