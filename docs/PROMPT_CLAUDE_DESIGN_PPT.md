Eres un diseñador experto en presentaciones. Voy a darte el design system de mi producto web y quiero que me ayudes a crear un design system para PowerPoint/Google Slides que sea visualmente coherente con él.

## Mi Design System Web

### Colores principales

- **Fondo de página**: `#EEF1F4` — gris azulado frío, nunca blanco puro
- **Superficie / tarjeta**: `#FFFFFF` — el blanco es para paneles, no para el fondo
- **Texto principal**: `#0F172A` — Slate 900, negro con cast frío azulado
- **Texto secundario**: `#475569` — Slate 600
- **Texto muted**: `#94A3B8` — Slate 400, labels y metadata
- **Borde**: `#E8ECF0` — gris claro para dividers

### Color de marca — UPC Red

- **Primary**: `#D50000` — rojo UPC, color de marca principal
- **Primary hover**: `#B80000`
- **Primary soft**: `#FFEAEA` — fondo suave para highlights

### Colores de acento (usados en gráficas y avatares)

- **Blue**: `#3B82F6` / soft `#DBEAFE`
- **Violet**: `#8B5CF6` / soft `#EDE9FE`
- **Amber**: `#F5A623` / soft `#FEF0D4`
- **Coral**: `#FF7A6E` / soft `#FFE7E3`
- **Mint/Green**: `#4ADE80` / soft `#DCFCE7`
- **Success**: `#16A34A`

### Tipografía

- **Fuente única**: Inter (sin serif, sin monospace)
- **Pesos**: 400 body · 500 énfasis · 600 semibold/headings · 700 títulos fuertes
- **Escala**: 11px labels uppercase · 14px body default · 18px subtítulos · 22px sección · 28px heading de página
- **Letter-spacing**: −0.6px en 28px · −0.4px en 22px · +0.6px en labels uppercase de 11px

### Forma y estilo de componentes

- **Radio dominante**: 24px para cards, paneles y contenedores grandes
- **Botones**: pill shape (border-radius 9999px) — nunca cuadrados
- **Sin sombras** en cards — el contraste de color (`#FFFFFF` sobre `#EEF1F4`) hace la separación
- **Gradientes**: solo en avatares — Violet→Blue (`#8B5CF6`→`#3B82F6`) o Coral→Amber (`#FF7A6E`→`#F5A623`)
- **Iconos**: Lucide, outline, nunca rellenos

### Estilo visual general

- Limpio, moderno, frío-neutral (paleta Slate, no Stone ni Zinc)
- El rojo `#D50000` aparece de forma puntual: logo, botón primario, badge de notificación
- Ningún gradiente en fondos ni botones — solo en avatares
- Todo lo que "flota" es blanco sobre el fondo gris azulado

---

Con esta base, diseña para mí un design system de presentaciones que incluya:

1. **Paleta de colores para slides** — colores de fondo, texto, primario, acento, y semánticos (éxito, alerta, info), con sus hex codes listos para configurar en PowerPoint/Google Slides

2. **Tipografía para slides** — fuente, tamaños y pesos para: título de portada, título de sección, título de slide, body, caption/nota, dato numérico destacado

3. **Layouts base** — describe los 5–6 layouts de slide más útiles: portada, agenda/índice, contenido con texto, contenido con imagen o gráfica, slide de datos/métricas, slide de cierre

4. **Componentes visuales** — especificación de: badges de estado, tabla de datos, bloque de cita/highlight, callout de alerta, callout de éxito, separadores de sección

5. **Reglas de uso** — qué hacer y qué evitar para mantener coherencia con el producto web

6. **Configuración del tema en PowerPoint/Google Slides** — los valores exactos para configurar: 6 colores del tema + 2 de texto, fuente de encabezado y fuente de cuerpo

El objetivo es que las diapositivas parezcan parte del mismo mundo visual que la app. El tono es académico-profesional: es una tesis universitaria sobre un chatbot de matrícula para la Universidad Peruana de Ciencias Aplicadas (UPC).
