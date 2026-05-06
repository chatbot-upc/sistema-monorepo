# Do & Don't — Chatbot UPC Admin

Reglas no negociables del sistema. Si una decisión de diseño contradice una regla aquí, prevalece esta regla.

---

## 1. Mono para metadata, sans para prosa

**DO** usar `font-mono` para todo lo que es dato técnico: teléfonos, timestamps, conv_id, scores, latencias, tokens.

```tsx
<span className="font-mono text-xs text-muted">+51 999 888 777</span>
<span className="font-mono text-xs text-muted">09:14 · 1.2s</span>
<span className="font-mono text-xs text-muted">conv_a3f8d2 · p95 240ms</span>
```

**DON'T** usar Inter para teléfonos, IDs o métricas.

```tsx
{/* ❌ Pierde la identidad de "dato técnico" y los dígitos no alinean */}
<span className="font-sans text-sm">+51 999 888 777</span>
```

---

## 2. Naranja `signal` solo para "necesita humano"

**DO** reservar `signal` (#D9502C) para: pill `escalated`, fila de conversación escalada, intent con confidence < 0.55, errores de sistema, button destructive.

```tsx
<span className="bg-signal-soft text-signal border border-signal/30 px-2 rounded-xs">
  ESCALATED
</span>
```

**DON'T** usar `signal` como acento decorativo, hover de botón, link, badge de "nuevo", o resaltar info no urgente.

```tsx
{/* ❌ Diluye el significado del color: cuando llegue una escalada real ya no destaca */}
<button className="bg-signal text-white">Subir documento</button>
```

---

## 3. Newsreader (serif) solo en el hero del dashboard

**DO** usar Newsreader **únicamente** en el número grande del dashboard de inicio (HU31).

```tsx
<div className="font-serif text-display tabular-nums">247</div>
```

**DON'T** usar serif en headings de secciones, cards, modales, ni en cualquier otro número.

```tsx
{/* ❌ Rompe la consistencia y hace el hero del dashboard menos especial */}
<h2 className="font-serif text-2xl">Conversaciones</h2>
```

---

## 4. Bordes 1px, no sombras

**DO** separar superficies con `border-line` 1px. Las cards, tablas, sidebars son planas.

```tsx
<div className="bg-surface border border-line rounded-lg p-5">…</div>
```

**DON'T** poner sombras en cards estáticas. Las sombras (`shadow-overlay`, `shadow-modal`) son **solo** para overlays que flotan: dropdowns, modales, toasts.

```tsx
{/* ❌ Look genérico de Bootstrap 2014 */}
<div className="bg-surface shadow-md rounded-lg p-5">…</div>
```

---

## 5. Densidad alta en CRM

**DO** mantener filas de tabla en 48-56px, padding compacto, line-heights apretados. El admin va a vivir en estas pantallas — debe caber mucha info en un pantallazo.

```tsx
<tr className="h-14"> {/* 56px */}
  <td className="px-4 text-sm">…</td>
</tr>
```

**DON'T** importar paddings de marketing/landing. No es Stripe.com; es la herramienta interna que va a usar la coordinadora todo el día.

```tsx
{/* ❌ Filas de 80px desperdician viewport */}
<tr className="h-20"><td className="px-8 py-6">…</td></tr>
```

---

## 6. Botón primary negro, único por contexto

**DO** usar máximo **un** botón `primary` (`bg-accent`) visible por pantalla, asignado a la acción más importante.

```tsx
<div className="flex gap-3">
  <Button variant="secondary">Cancelar</Button>
  <Button variant="primary">Guardar cambios</Button>
</div>
```

**DON'T** poner dos primarys uno al lado del otro. Si dos acciones son igual de importantes, las dos van como `secondary`.

```tsx
{/* ❌ Compiten — el ojo no sabe a dónde ir */}
<Button variant="primary">Editar</Button>
<Button variant="primary">Duplicar</Button>
```

---

## 7. Fila escalada se ve diferente, no solo el pill

**DO** pintar la fila completa de la lista de conversaciones con `bg-signal-soft` cuando está escalada. El pill solo no es suficiente — la fila debe gritar desde 5 filas de distancia.

```tsx
<tr className={cn("hover:bg-surface-2", convo.status === "escalated" && "bg-signal-soft hover:bg-signal-soft/80")}>
  …
</tr>
```

**DON'T** señalar escalado solo con el badge.

```tsx
{/* ❌ Si hay 30 filas el pill se pierde — los humanos escanean por color de fila, no por badge */}
<tr><td>…<EscalatedPill /></td></tr>
```

---

## 8. Confidence baja sin texto colorido es ambiguo

**DO** mostrar score < 0.55 con `text-signal` Y poner la etiqueta `fallback` en el chip. El admin debe identificar de un vistazo cuándo el bot no entendió.

```tsx
<span className={cn("font-mono text-xs", score < 0.55 && "text-signal")}>
  {intent} {score.toFixed(2)}
</span>
```

**DON'T** mostrar todos los scores en el mismo color y esperar que el admin compare cifras manualmente.

```tsx
{/* ❌ 0.41 vs 0.78 requiere lectura activa; con color es preatencional */}
<span className="font-mono text-xs text-muted">{intent} {score.toFixed(2)}</span>
```

---

## 9. Empty states con copy contextual, no genérico

**DO** escribir empty states que expliquen qué hacer y por qué la pantalla está vacía.

```tsx
<EmptyState
  icon={<MessageSquare />}
  title="Sin conversaciones aún"
  description="Cuando un estudiante escriba al WhatsApp aparecerá aquí."
/>
```

**DON'T** escribir empty states genéricos.

```tsx
{/* ❌ No ayuda al admin a entender si hay un bug o si el sistema está bien */}
<EmptyState title="No hay datos" description="Lista vacía" />
```

---

## 10. Usar tokens, nunca valores hardcodeados

**DO** referenciar tokens del sistema para todo color, espaciado, tamaño y radius.

```tsx
<div className="bg-surface border border-line rounded-lg p-4 gap-3">
  <p className="text-sm text-muted">Helper text</p>
</div>
```

**DON'T** hardcodear valores arbitrarios.

```tsx
{/* ❌ Cuando cambie un token el cambio no se propaga */}
<div className="bg-white border border-[#E4E4E7] rounded-[7px] p-[15px] gap-[11px]">
  <p className="text-[13px] text-[#71717A]">Helper text</p>
</div>
```

---

## Resumen visual

| Hacer | Evitar |
|---|---|
| Mono para datos | Inter para teléfonos / IDs |
| Naranja para escaladas | Naranja para decorar |
| Newsreader solo en hero | Serif en headings |
| Bordes 1px | Sombras en cards |
| Filas 48-56px | Padding de marketing |
| 1 primary por pantalla | 2 primarys juntos |
| Fila escalada con bg | Solo pill de escalada |
| Confidence baja en signal | Todos los scores iguales |
| Empty state contextual | "No hay datos" |
| Tokens del sistema | Valores hardcodeados |
