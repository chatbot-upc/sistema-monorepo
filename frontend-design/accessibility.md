# Accessibility — Chatbot UPC Admin

Checklist mínima WCAG 2.1 AA aplicable al CRM. Marca todos los puntos antes de cada sprint review.

---

## Contraste

Verificado con la paleta `tokens.md`. Pares válidos AA:

| Texto sobre fondo | Ratio | Estado |
|---|---|---|
| `fg #0A0A0A` sobre `bg #FFFFFF` | 19.3:1 | ✅ AAA |
| `fg-2 #3F3F46` sobre `bg #FFFFFF` | 10.8:1 | ✅ AAA |
| `muted #71717A` sobre `bg #FFFFFF` | 4.8:1 | ✅ AA |
| `muted #71717A` sobre `surface-2 #FAFAFA` | 4.6:1 | ✅ AA (justo) |
| `muted-2 #A1A1AA` sobre `bg #FFFFFF` | 2.8:1 | ❌ **Solo placeholders e iconos decorativos** |
| `accent-fg #FFFFFF` sobre `accent #0A0A0A` | 19.3:1 | ✅ AAA |
| `signal #D9502C` sobre `bg #FFFFFF` | 4.5:1 | ✅ AA (justo) |
| `signal #D9502C` sobre `signal-soft #FFF1EE` | 4.3:1 | ⚠️ Sub-AA — solo en pills donde el texto es ≥18px o ≥14px bold |
| `success #16A34A` sobre `success-soft #F0FDF4` | 4.5:1 | ✅ AA |

### Reglas

- **Nunca** usar `muted-2` para texto informativo. Solo placeholders, disabled state y iconos decorativos.
- Pills `escalated` y `closed` con texto pequeño (`text-2xs` mono) deben usar `font-bold` o aumentar a `text-xs` para cumplir AA.
- Verificar contraste cada vez que se agregue un color nuevo (no debería pasar — la paleta está cerrada).

---

## Focus visible

- **Todo** elemento interactivo debe tener focus ring visible al navegar con teclado: 2px `accent` con offset 2px (definido en `globals.css`).
- Nunca usar `outline: none` sin reemplazo equivalente.
- En elementos sobre `accent` (botón primary), invertir: ring `bg` con offset 2px.
- Skip link al inicio del DOM: "Saltar al contenido" oculto hasta focus, salta a `<main>`.

---

## Targets táctiles

- Botones e items interactivos: mínimo **40px** alto en pantalla. Tamaño `sm` (28-32px) solo permitido en toolbars con espacio constreñido.
- Items de tabla con click: el `tr` entero es el target (no solo el texto).
- Iconos clickeables sin label: padding mínimo para llegar a 32x32 área de hit.

---

## Jerarquía semántica

- Una sola `<h1>` por página = el page header.
- `<h2>` para secciones mayores dentro de la página.
- `<h3>` para títulos de cards.
- No saltar niveles (h1 → h3 sin h2).
- `<main>` envuelve el área de contenido (no incluye sidebar ni topbar).
- `<nav>` para sidebar y breadcrumb.
- `<aside>` para columnas auxiliares (lista en thread layout).

---

## Teclado

### Tabla

- `Tab` → enfoca primera fila.
- `↓` / `↑` → navega entre filas (sin abrir).
- `Enter` → abre / selecciona la fila enfocada.
- `Esc` → deselecciona.

### Modal

- Auto-focus al primer input al abrir.
- `Esc` → cierra (excepto en modales destructivos donde requiere confirmación explícita).
- Focus trap: tab cycle dentro del modal, no escapa.
- Al cerrar, devolver focus al elemento que lo abrió.

### Thread

- `Cmd+Enter` (mac) / `Ctrl+Enter` (win) → enviar mensaje.
- `↑` en textarea vacío → editar último mensaje admin (si existe).
- `j` / `k` → navegar entre conversaciones de la lista (Linear-style).

### Search global

- `Cmd+K` / `Ctrl+K` → enfocar search del topbar desde cualquier pantalla.
- `Esc` dentro de search → limpiar y desenfocar.

---

## Screen readers

- Toda imagen `<img>` con `alt`. Iconos decorativos: `aria-hidden="true"`.
- Iconos de acción sin label: `aria-label="Cerrar"`, `aria-label="Editar intención fechas_pago"`.
- Estado de pills comunicado: `<span role="status" aria-label="Conversación escalada">ESCALATED</span>`.
- Loading: `aria-busy="true"` en el contenedor + `<span class="sr-only">Cargando</span>`.
- Toasts: `role="status"` para info/success, `role="alert"` para error.
- Live region para nuevas escaladas en tiempo real: `<div role="status" aria-live="polite" aria-atomic="true">`.

---

## Forms

- Label asociado a input via `<label for>` o wrapping.
- Error message asociado via `aria-describedby={errorId}` y `aria-invalid="true"`.
- Required: `aria-required="true"` además del asterisco visual.
- Helper text también asociado via `aria-describedby`.
- Agrupar radios y checkboxes con `<fieldset>` + `<legend>`.

---

## Movimiento y animación

- Respetar `prefers-reduced-motion: reduce`:
  - Eliminar transiciones de slide/scale.
  - Mantener fades < 100ms.
  - Eliminar pulse de notificaciones.
- Ninguna animación dura más de 400ms.
- Auto-scroll al recibir mensaje: solo si el usuario está cerca del final (no robar control).

---

## Idioma

- `<html lang="es-PE">` en el root.
- Texto en español neutro de Perú. Errores y mensajes formales sin tutear.
- Números con formato local: `1,240` con coma, montos `S/ 1,240.00`.
- Fechas: formato corto `27/04/2026` o largo `lunes 27 de abril, 2026`.

---

## Pruebas mínimas antes de PR

1. ✅ Navegar la pantalla completa solo con teclado.
2. ✅ Pasar la pantalla por axe-core (`@axe-core/react` en dev) — 0 violaciones críticas.
3. ✅ Probar con `prefers-reduced-motion: reduce` en DevTools.
4. ✅ Probar zoom 200% — no debe haber overflow horizontal ni texto cortado.
5. ✅ Probar con VoiceOver (mac) en al menos un flujo crítico (login, ver conversación escalada).

---

## Fuera de alcance (por ser tesis)

Estos puntos quedan documentados como deuda conocida pero no son bloqueantes para la entrega de tesis:

- WCAG AAA (solo se busca AA).
- Modo alto contraste personalizado.
- Soporte de lectores de pantalla en Windows (NVDA/JAWS) — solo se valida con VoiceOver.
- Internacionalización completa — la app es solo español.
