# Patterns — Chatbot UPC Admin

Patrones compuestos que combinan los componentes de `components.md` para resolver pantallas reales del backlog.

---

## P1. App shell

Layout base de toda la app autenticada.

```
┌──────────────────────────────────────────────────────────────┐
│ Topbar  56px                                                 │  z-sticky
├──────────┬───────────────────────────────────────────────────┤
│          │                                                   │
│ Sidebar  │  Content                                          │
│  240px   │  max-width 1440px, padding space-8, mx-auto       │
│          │                                                   │
│          │                                                   │
└──────────┴───────────────────────────────────────────────────┘
```

### CSS grid

```css
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  grid-template-rows: var(--topbar-h) 1fr;
  grid-template-areas:
    "sidebar topbar"
    "sidebar content";
  min-height: 100vh;
}
```

- Sidebar ocupa filas 1 y 2 (`grid-row: span 2`) — el logo del sidebar está alineado con la altura del topbar.
- Content scrollea independientemente del sidebar.
- Sidebar y topbar `border-line` separadores.

---

## P2. Login (HU18)

Una sola columna centrada. Sin sidebar ni topbar.

```
┌──────────────────────────────────────┐
│                                      │
│           [Logo · 32px]              │
│                                      │
│      Panel de matrícula UPC          │   text-2xl font-semibold
│      Inicia sesión para continuar    │   text-sm muted
│                                      │
│   ┌────────────────────────────┐    │
│   │ Email                       │    │   Card default · 400px
│   │ [input lg]                  │    │
│   │                             │    │
│   │ Contraseña                  │    │
│   │ [input lg]                  │    │
│   │                             │    │
│   │ [Entrar — primary lg full] │    │
│   └────────────────────────────┘    │
│                                      │
│   v0.1.0 · Tesis UPC · 2026          │   text-2xs mono muted-2
│                                      │
└──────────────────────────────────────┘
```

- Container vertical centrado, `min-height: 100vh`, gap `space-6`.
- Card width 400px, padding `space-8`, gap interno `space-4`.
- Form submit con Enter; error inline debajo del card en toast `error`.

---

## P3. Dashboard del día (HU31)

```
┌──────────────────────────────────────────────────────────────┐
│ Inicio · Lunes 27 de abril                              ⌘K │   Topbar
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CONVERSACIONES HOY                              +12 vs ayer │   Hero card xl
│                                                              │
│       247                                                    │   Newsreader 84px
│                                                              │
│       42 escaladas · 198 resueltas · 7 activas               │   text-sm mono muted
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ │   Grid 4 stat cards
│ │ TASA       │ │ LATENCIA   │ │ CONFIANZA  │ │ TOKENS     │ │
│ │ FALLBACK   │ │ P95        │ │ PROMEDIO   │ │ HOY        │ │
│ │   8.2%     │ │   1.4s     │ │   0.81     │ │   142k     │ │
│ │ -2pp       │ │ -120ms     │ │ +0.03      │ │ ~$0.84     │ │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘ │
├──────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐  ┌─────────────────────────┐    │   Grid 2 cols
│ │ Última escalada    ver →│  │ Conversaciones recientes│    │
│ │ ─────────────────────── │  │ ─────────────────────── │    │
│ │ +51 999 ··· · hace 3min │  │ [Conv row · activa]     │    │
│ │ "no entiendo el cargo  │  │ [Conv row · activa]     │    │
│ │  por reincorporación"   │  │ [Conv row · cerrada]    │    │
│ │                         │  │ [Conv row · escalada]   │    │
│ │ confianza 0.34          │  │ [Conv row · cerrada]    │    │
│ └─────────────────────────┘  └─────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

- Hero: card variante `hero` (xl radius, sin border, padding 32). Una sola fila full-width.
- 4 stat cards en grid 4col gap `space-4`.
- 2 cards bottom en grid 2col gap `space-6`. Card izq variante `default`. Card der variante `flush` con conv rows internas.

### Layout responsive

- `lg`: stats 2x2, bottom apilado.
- `xl`+: como descrito.

---

## P4. Lista de conversaciones (HU27, HU23) — vista standalone

```
┌──────────────────────────────────────────────────────────────┐
│ Conversaciones                                               │   Page header
│ Todas las conversaciones del chatbot                          │
├──────────────────────────────────────────────────────────────┤
│ [Search 320px]  [Estado: Todos ▾]  [Fecha ▾]    [Exportar]  │   Toolbar sticky
├──────────────────────────────────────────────────────────────┤
│ TELEFONO        │ ULTIMO MENSAJE         │ ESTADO  │ HORA   │   Table header
│ ─────────────────────────────────────────────────────────── │
│ +51 999 888 777 │ "cuando es el pago..." │ ACTIVE  │ 09:15  │
│ +51 988 777 666 │ "no entiendo el..."    │ ESCALAT │ 09:12  │   bg signal-soft
│ +51 977 666 555 │ "gracias!"             │ CLOSED  │ 09:08  │
│ ...                                                          │
├──────────────────────────────────────────────────────────────┤
│ Página 1 de 14 · 25 por página                              │   Pagination
└──────────────────────────────────────────────────────────────┘
```

### Toolbar

- Container horizontal, gap `space-3`, padding `space-4 0`, sticky top `var(--topbar-h)`, `bg-bg`, `border-bottom 1px line`.
- Search izquierda, filtros centro (chips dropdown), CTA secundaria derecha.

### Filter chips

- Estilo: button `secondary sm` con icon `ChevronDown` derecho.
- Activos: `bg-surface-2`, label muestra valor seleccionado.
- Limpiar filtros: link `text-sm muted` solo visible cuando hay filtros activos.

---

## P5. Vista detalle conversación (HU28, HU29) — split

```
┌──────────────────────────────────────────────────────────────┐
│ Topbar                                                       │
├───────────────────────────┬──────────────────────────────────┤
│ [Search]                  │ +51 999 888 777   [ESCALATED]   │   Thread header
│ ─────────────────────────│ ─────────────────────────────── │
│ [Conv row · activa] ◀ sel│                                  │
│ [Conv row]                │  [bubble student]                │
│ [Conv row · escalada]     │  [bubble bot]                    │
│ [Conv row · cerrada]      │  [bubble student]                │
│ [Conv row]                │  ─── notice: escalada 09:16 ─── │
│ ...                       │  [bubble admin]                  │
│                           │  [bubble student]                │
│                           │                                  │
│                           │ ─────────────────────────────── │
│                           │ [textarea] [Enviar]              │   Reply area
└───────────────────────────┴──────────────────────────────────┘
   col 1: 360px              col 2: 1fr (max 800px contenido)
```

### CSS grid

```css
.thread-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  height: calc(100vh - var(--topbar-h));
}
```

- Columna izq: lista densa scrolleable, `border-right 1px line`.
- Columna der: thread header sticky top, body scrolleable, reply area sticky bottom.
- Ancho del bloque de bubbles: `max-width: 720px`, `margin: 0 auto`.
- Auto-scroll al último mensaje al abrir la conversación.
- Cuando llega un mensaje nuevo del estudiante, scroll suave hacia abajo solo si el usuario ya está cerca del final (threshold 120px); si no, mostrar botón flotante "↓ Nuevo mensaje".

---

## P6. Documentos RAG (HU14-17)

```
┌──────────────────────────────────────────────────────────────┐
│ Documentos                                  [Subir documento]│   Header + CTA
│ Fuentes que el chatbot consulta para responder                │
├──────────────────────────────────────────────────────────────┤
│ [Search]  [Tipo ▾]  [Estado ▾]                              │
├──────────────────────────────────────────────────────────────┤
│ NOMBRE          │ TIPO  │ TAMANO │ ESTADO   │ INDEXADO       │
│ ───────────────────────────────────────────────────────────  │
│ matricula.pdf   │ PDF   │ 1.2 MB │ INDEXED  │ 2026-04-25    │
│ aranceles.pdf   │ PDF   │ 840 KB │ INDEXING │ —             │
│ faqs.md         │ MD    │ 12 KB  │ DRAFT    │ —             │
└──────────────────────────────────────────────────────────────┘
```

### Upload modal (lg)

- Dropzone: contenedor full-width, `border 2px dashed line-2`, `radius-lg`, padding `space-12`, centrado.
- Estados:
  - idle: icon `UploadCloud` 24px muted + texto "Arrastra archivos o haz clic" + helper "PDF, MD, TXT · máx 10MB".
  - dragover: `border-accent`, `bg-surface-2`.
  - uploading: progress bar lineal `accent` + nombre archivo.
  - error: `border-signal`, mensaje en `signal`.
- Lista de archivos a subir debajo del dropzone con button remove ghost sm por item.

---

## P7. Intenciones SBERT (HU09-13)

Lista editable con sample utterances expandibles.

```
┌──────────────────────────────────────────────────────────────┐
│ Intenciones                              [Nueva intención]   │
├──────────────────────────────────────────────────────────────┤
│ ▾ fechas_pago                                  [Editar]     │
│   ──────────────────────────────────────                    │
│   42 ejemplos · umbral 0.65 · activa                         │   meta mono xs
│   ┌──────────────────────────────────────────────┐          │
│   │ "cuando es el pago del primer ciclo"          │          │   sample chips
│   │ "fecha límite de pago"                        │          │
│   │ "hasta cuando puedo pagar"                    │          │
│   │ ... +39 más                                    │          │
│   └──────────────────────────────────────────────┘          │
│                                                              │
│ ▸ aranceles                                                 │
│ ▸ requisitos                                                │
└──────────────────────────────────────────────────────────────┘
```

- Cada intent es un Card `compact` colapsable.
- Header de card: `[chevron] [nombre intent · text-lg font-medium] [meta] [Editar]`.
- Expansión: animación height 240ms.

---

## P8. Reportes (HU32)

```
┌──────────────────────────────────────────────────────────────┐
│ Reportes                                    [Exportar Excel] │
├──────────────────────────────────────────────────────────────┤
│ Rango: [Desde dd/mm/yyyy] — [Hasta dd/mm/yyyy] [Aplicar]    │
├──────────────────────────────────────────────────────────────┤
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                 │   Stats summary
│ │ Total  │ │ Resuel │ │ Escala │ │ Tasa F │                 │
│ │ 4,231  │ │ 3,890  │ │ 287    │ │ 8.1%   │                 │
│ └────────┘ └────────┘ └────────┘ └────────┘                 │
├──────────────────────────────────────────────────────────────┤
│ Conversaciones por día                                       │
│ ┌──────────────────────────────────────────────────────┐    │   Bar chart card
│ │ ▇ ▇▇ ▇ ▆ ▇▇▇▇ ▇ ▆▇▇                                  │    │
│ └──────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────┤
│ Intenciones más frecuentes                                   │   Table card
│ ───────────────────────────────────────────────────────     │
│ fechas_pago    · 1,240 (29%)  ▇▇▇▇▇▇▇▇▇▇▇▇▇                │
│ aranceles      ·   890 (21%)  ▇▇▇▇▇▇▇▇                      │
│ ...                                                          │
└──────────────────────────────────────────────────────────────┘
```

- Date range: 2 inputs `md` con icon `Calendar`, button `primary md` "Aplicar".
- Charts: barras horizontales con `bg-surface-2` track + `bg-accent` fill, label izq + valor mono der.
- Export: button `secondary md` con icon `Download`. Genera Excel/CSV en backend, abre en nueva pestaña.

---

## P9. Notification flow (Firebase push)

Cuando llega una escalada nueva en tiempo real:

1. Bell icon en topbar muestra badge contador `+1` con animación pulse `signal-soft` 2s.
2. Toast `error` aparece bottom-right: "Nueva escalada · +51 999 888 777" con button `Ver` que navega al thread.
3. Lista de conversaciones (si está abierta): nueva fila aparece arriba con animación slide-down 240ms y bg `signal-soft` que persiste.
4. Sound: NO. Es CRM, no chat consumer.

---

## P10. Loading states

- Tabla cargando: 8 skeleton rows con altura igual a row real.
- Card cargando: skeleton del header + skeleton de stats con la misma estructura.
- Thread cargando: 3 skeleton bubbles alternando lados.
- Botón en submit: `loading` state con `Loader2` animado.
- Page-level: barra superior 2px `accent` con animación indeterminate (estilo Vercel/Linear).

---

## Reglas comunes a todas las pantallas

1. **Page header** = `text-2xl font-semibold` + subtítulo `text-sm muted` + acción primaria a la derecha alineada.
2. **Toolbars** sticky bajo el topbar (`top: var(--topbar-h)`).
3. **Page padding** = `space-8` horizontal y vertical.
4. **Max content width** = `1440px` centrado con `mx-auto`.
5. **Vacíos** siempre con Empty state, nunca con texto pelado.
6. **Errores fatales** (500, network) ocupan toda la página con icon + título + descripción + botón "Reintentar".
