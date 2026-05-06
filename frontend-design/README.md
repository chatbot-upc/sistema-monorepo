# Frontend Design System — Chatbot UPC Admin

Design system del panel administrativo del Chatbot de matrícula UPC (tesis).

## Archivos

| Archivo | Contenido |
|---|---|
| [`tokens.md`](./tokens.md) | Tokens de color, tipografía, espaciado, radius, sombras, z-index, breakpoints. |
| [`tailwind.config.ts`](./tailwind.config.ts) | Config Tailwind mapeando los tokens al theme. |
| [`globals.css`](./globals.css) | Variables CSS root, reset mínimo, estilos base. |
| [`components.md`](./components.md) | Especificación de 14 componentes + auxiliares. |
| [`patterns.md`](./patterns.md) | 10 patrones compuestos por pantalla del backlog. |
| [`accessibility.md`](./accessibility.md) | Checklist WCAG AA. |
| [`do-and-dont.md`](./do-and-dont.md) | 10 reglas no negociables. |

## Stack objetivo

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS (config en este folder)
- shadcn/ui como base de componentes
- Lucide React para iconos
- Inter + JetBrains Mono + Newsreader vía `next/font/google`

## Cobertura del backlog

### ✅ Cubierto por el system

| HU | Pantalla | Componentes / patrones usados |
|---|---|---|
| HU18 | Login | P2 · Card, Input, Button |
| HU24 | JWT auth (sin UI propia) | n/a (backend) |
| HU25 | Firebase config (sin UI propia) | n/a (backend) |
| HU27 | Lista de conversaciones | P4 · Table, Pill, Conversation row, Toolbar filters |
| HU23 | Distinción visual de escaladas | P4 · regla #7 do-and-dont (fila bg signal-soft) |
| HU28 | Detalle de conversación | P5 · Chat bubble, Thread layout |
| HU29 | Tomar control / responder | P5 · Reply area sticky, Notice divider |
| HU31 | Dashboard del día | P3 · Stat card, Hero card con Newsreader, Conversation row |
| HU32 | Reportes por rango | P8 · Date range, Bar chart card, Stats summary, Export button |
| HU14-17 | Documentos RAG | P6 · Table, Upload modal con dropzone |
| HU09-13 | Intenciones SBERT | P7 · Card colapsable con sample chips |

### ⚠️ Gaps conocidos (no documentados en este ciclo)

Estos requieren componentes adicionales si la HU los exige. Ninguno bloquea Sprint 1; la mayoría caen en Sprint 4-5.

1. **Curva de aprendizaje SBERT (HU13)**: si el backlog pide visualizar accuracy por época durante el reentrenamiento, hay que agregar un line chart simple. El `.pen` actual no contempla line charts, y nuestra guía dice que no son fáciles en flexbox; habría que usar Recharts o similar.
2. **Drag-and-drop reordenable de intenciones**: si la HU pide priorizar intenciones por arrastre, falta especificar el handle visual y el feedback de "drop zone".
3. **Audit log / actividad del admin**: ninguna HU lo pide explícitamente, pero si se agrega para tesis, faltaría un componente Timeline.
4. **Onboarding del admin** (primer login, configuración inicial): no documentado. Si el jurado lo pide, reusar Modal `lg` + Stepper (que tampoco está documentado — agregar si aplica).
5. **Configuración del bot (prompt, modelo, umbral SBERT global)**: si HU03/HU04 incluyen UI para tunear parámetros, falta un patrón de "settings page" con secciones tipo Linear settings.
6. **Toaster con scroll/historial**: el patrón solo describe stack de 3. Si se necesita ver historial completo de notificaciones (panel lateral), falta especificar.
7. **Comparación intent SBERT vs LLM** (métrica clave de tesis): faltaría una vista comparativa side-by-side. Hay tokens y componentes para construirla, pero no está prefigurada como patrón.

## Cómo extender

1. Si necesitas un componente nuevo, primero verifica que no se pueda componer con los existentes.
2. Si requiere un token nuevo, justifícalo en el PR contra los tokens existentes.
3. Mantén `tokens.md` y los archivos como fuente de verdad — el `.pen` y este folder deben evolucionar juntos.
4. Cualquier color fuera de la paleta cerrada requiere aprobación explícita.

## Referencias visuales del sistema

- Vercel · https://vercel.com (densidad, neutralidad, focus tipográfico)
- Linear (light mode) · https://linear.app (sidebar nav, command palette)
- Read.cv · https://read.cv (uso del serif como acento puntual)
- Stripe Atlas · https://stripe.com/atlas (cards minimalistas, jerarquía)
