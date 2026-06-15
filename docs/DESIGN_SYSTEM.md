# Design System — Chatbot UPC Admin (`final-design.pen`)

---

## Paleta de colores

### Fondos y superficies

| Token | Hex | Uso |
|---|---|---|
| `--bg` | `#F6F8FA` | Fondo base (cool gray muy claro) |
| `--bg-2` | `#EEF1F4` | Fondo de página — usado en todos los screens como background del layout |
| `--surface` | `#FFFFFF` | Tarjetas, sidebars, paneles, tablas |
| `--surface-2` | `#F6F8FA` | Inputs, hover sutil, filas alternas |

### Texto

| Token | Hex | Uso |
|---|---|---|
| `--fg` | `#0F172A` | Texto principal — Slate 900, negro con cast azulado-frío |
| `--fg-2` | `#475569` | Texto secundario — Slate 600 |
| `--muted` | `#94A3B8` | Labels, section headers, metadata — Slate 400 |
| `--muted-2` | `#CBD5E1` | Placeholders, deshabilitado — Slate 300 |
| `--ink` | `#1C1917` | Botón oscuro de acción (upload, CTA secundario) |

### Primario — UPC Red

| Token | Hex | Uso |
|---|---|---|
| `--primary` | `#D50000` | Color de marca. Botón principal, logo icon, nav item activo, badges |
| `--primary-hover` | `#B80000` | Hover sobre elementos primarios |
| `--primary-soft` | `#FFEAEA` | Fondo suave para alerts o highlights de primary |

### Bordes

| Token | Hex | Uso |
|---|---|---|
| `--line` | `#E8ECF0` | Borde por defecto, dividers de tabla |
| `--line-2` | `#D8DEE5` | Borde de énfasis, hover de inputs |

### Semánticos

| Token | Hex | Uso |
|---|---|---|
| `--success` | `#16A34A` | Estado positivo, métricas verdes |
| `--blue` | `#3B82F6` | Informativo, links secundarios |
| `--blue-soft` | `#DBEAFE` | Fondo de badge informativo |
| `--amber` | `#F5A623` | Advertencia, pendiente |
| `--amber-soft` | `#FEF0D4` | Fondo de notas internas / warning |
| `--coral` | `#FF7A6E` | Acento visual — usado en gradientes de avatar |
| `--violet` | `#8B5CF6` | Acento visual — usado en gradientes de avatar |

### Gradientes de avatar

| Nombre | Colores | Uso |
|---|---|---|
| Violet→Blue | `#8B5CF6` → `#3B82F6` (135°) | Avatar de usuario administrador |
| Coral→Amber | `#FF7A6E` → `#F5A623` (0°) | Avatar de estudiante / contacto |

---

## Tipografía

### Familia

**Inter** — fuente única para toda la UI. Sin fuente serif ni mono en el diseño final.

### Escala

| Tamaño | Peso | Letter-spacing | Uso |
|---|---|---|---|
| 11px | 600 | +0.6px | Section labels UPPERCASE (INFORMACIÓN ACADÉMICA, ETIQUETAS) |
| 12px | 400 | 0 | Captions, versión de app, texto muy pequeño |
| 13px | 400–500 | 0 | Links secundarios (Forgot password), metadata |
| **14px** | **400–600** | **0** | **Body default, nav items, body de tabla — DEFAULT** |
| 15px | 600 | 0 | Label de botón CTA principal |
| 18px | 700 | 0 | Brand mark / logo del sidebar |
| 20px | 700 | 0 | Títulos de panel, nombre de contacto |
| 22px | 700 | -0.4px | Section heading |
| 28px | 600 | -0.6px | Page heading (Documentos, Reportes...) |

### Pesos

| Valor | Uso |
|---|---|
| 400 | Body, texto secundario, nav inactivo |
| 500 | Énfasis ligero, nav hover |
| 600 | Headings, botones, semibold |
| 700 | Brand mark, títulos fuertes, nombres |

---

## Botones

### Variantes

| Variante | Fondo | Texto | Radio | Alto | Uso |
|---|---|---|---|---|---|
| **Primary CTA** | `#D50000` | `#FFFFFF` | 23px (pill) | 46px | Acción principal: Iniciar sesión, Guardar |
| **Dark action** | `#1C1917` | `#FFFFFF` | 9999px (pill) | 40px | Acciones de tabla: Subir documento, Exportar |
| **Ghost / icon** | `#EEF1F4` | `#0F172A` | 9999px (pill) | 40px | Botones de icono en topbar, acciones secundarias |
| **Filter / selector** | `#FFFFFF` | `#0F172A` | 9999px (pill) | 40–44px | Selectores de filtro, date picker, search |

### Especificación de tamaños

| Variante | Padding horizontal | Font size | Font weight |
|---|---|---|---|
| Primary CTA | 0 (fill container) | 15px | 600 |
| Dark action | 18px | 14px | 500–600 |
| Ghost icon | centrado | — | — |
| Filter | 16–18px | 14px | 400–500 |

---

## Border radius

| Valor | Uso |
|---|---|
| **24px** | Cards, sidebars, paneles principales, tablas — **radio dominante de la UI** |
| 16px | Login card en mobile, inputs grandes |
| 12–14px | Nav items del sidebar |
| 10px | Logo icon box |
| **9999px** | Botones pill, search inputs, tabs, badges, avatares circulares |

---

## Espaciado

Base 4px.

| Valor | Uso típico |
|---|---|
| 4px | Gap mínimo entre elementos inline |
| 8px | Gap entre icon y label, padding de badges |
| 10px | Gap en nav items, gap en filas de info |
| 12px | Padding de nav items, gap entre stats |
| 14px | Padding de filas de tabla, padding de cards compactas |
| 16px | Padding del layout de página, gap entre columnas |
| 20px | Padding de cards, padding lateral de tabla, gap entre secciones |
| 24px | Padding de cards grandes, padding de chat |
| 28px | Padding de cards de intent/chart |
| 32px | Padding de login card (mobile) |

---

## Layout

| Variable | Valor |
|---|---|
| Viewport desktop | 1440 × 1080px |
| Viewport mobile | 390 × 844px |
| Sidebar ancho | 260px |
| Padding de página | 16px |
| Gap entre sidebar y contenido | 16px |
| Gap entre secciones verticales | 20px |

---

## Sidebar

- Fondo: `#FFFFFF`, radio 24px, padding `[20, 16, 16, 16]`
- Logo: Inter 18–20px weight 700, color `#0F172A` + icon box rojo `#D50000` radio 8–10px
- Nav item default: radio 12px, padding `[10, 12]`, icon `#94A3B8`, texto `#475569` weight 400
- Nav item activo: fondo `#EEF1F4`, texto `#0F172A` weight 600, icon `#0F172A`
- Nav item activo (Conversaciones): fondo `#D50000`, texto `#FFFFFF`, badge blanco
- Avatar de usuario: gradiente Violet→Blue, 36–40px, forma elipse

---

## Topbar

- Fondo: transparente sobre `#EEF1F4` de la página
- Search input: `#FFFFFF`, radio 9999, alto 44px, padding `[0, 18]`
- Date selector: `#FFFFFF`, radio 9999, alto 44px
- Botón notificaciones: `#FFFFFF`, radio 9999, 44 × 44px

---

## Cards y paneles

- Fondo: `#FFFFFF`, radio **24px**, padding 20–28px
- Sin sombra — separación visual por contraste de fondo (`#FFFFFF` sobre `#EEF1F4`)
- Gap interno entre elementos: 6–16px según densidad

---

## Tabla

- Contenedor: `#FFFFFF`, radio 24px
- Header: padding `[14, 20]`, texto `#94A3B8` 11px weight 600 uppercase
- Filas: padding `[12, 20]`, texto `#0F172A` / `#475569` 14px
- Dividers: rectángulo `#E8ECF0` de 1px de alto, full width
- Fila seleccionada: fondo `#EEF1F4`

---

## Badges / Pills

- Radio: 9999px (pill)
- Padding: `[2, 8]`
- Notificación: fondo `#D50000`, texto `#FFFFFF`, 11–12px weight 600
- Estado activo/tab: fondo `#0F172A`, texto `#FFFFFF`, 13–14px
- Estado inactivo/tab: sin fondo, texto `#475569`

---

## Iconos

- Librería: **Lucide**
- Tamaño: 20px en sidebar y topbar, 16px en acciones inline
- Color: hereda del texto (`#94A3B8` inactivo → `#0F172A` activo)

---

## Reglas generales

- Fondo de página siempre `#EEF1F4` — nunca blanco puro
- Cards siempre `#FFFFFF` sobre ese fondo — contraste sin sombras
- El único color de marca es `#D50000` — úsalo con moderación (logo, botón primario, nav activo)
- Todos los botones interactivos son **pill** (radius 9999) — no usar corners cuadrados en botones
- Radio de 24px para cualquier contenedor grande — es el lenguaje visual del producto
- Gradientes solo en avatares — nunca en fondos de UI ni botones
