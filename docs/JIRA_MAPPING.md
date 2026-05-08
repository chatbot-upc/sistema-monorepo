# Jira Tesis-UPC — Mapeo Epic / Sprint / Historia

> **Workspace:** [chatbotupc.atlassian.net](https://chatbotupc.atlassian.net) · **Proyecto:** Tesis-UPC (`SW`) · **Tipo:** Software next-gen · **Board ID:** 1
>
> **Totales:** 8 Epics · 5 Sprints · 46 Historias · Fuente: snapshot Jira al 2026-05-08.

---

## 1. Vista resumen

| | Epics | Historias |
|---|---|---|
| EP01 - Canal de Atención WhatsApp | SW-1 | 4 |
| EP02 - Comprensión del Lenguaje e Intenciones | SW-2 | 3 |
| EP03 - Base de Conocimiento y Generación de Respuestas | SW-3 | 11 |
| EP04 - Procesamiento Confiable e Infraestructura | SW-4 | 5 |
| EP05 - Escalado a Humano y Notificaciones | SW-5 | 5 |
| EP06 - Sistema Web de Administración | SW-6 | 9 |
| EP07 - Atención Personalizada por Perfil del Estudiante | SW-7 | 5 |
| EP08 - Consultas de Facturación y Pagos Pendientes | SW-8 | 4 |
| **TOTAL** | **8** | **46** |

| Sprint | Estado | Fechas | # Historias |
|---|---|---|---|
| S1 - Cimientos e Infra | 🟡 active | 2026-04-15 → 2026-05-01 | 4 |
| S2 - WhatsApp + NLU + Ingesta | 🔵 future | 2026-05-04 → 2026-05-22 | 9 |
| S3 - RAG, Memoria y Escalado | 🔵 future | 2026-05-25 → 2026-06-12 | 13 |
| S4 - Panel Admin + Perfil | 🔵 future | 2026-06-15 → 2026-06-26 | 15 |
| S5 - Facturación + Reportes | 🔵 future | 2026-06-29 → 2026-07-10 | 5 |
| **TOTAL** | | | **46** |

---

## 2. Mapeo por Epic

### EP01 - Canal de Atención WhatsApp (`SW-1`)
> El chatbot recibe y responde mensajes de los estudiantes por WhatsApp. Modulo M1. Objetivos OE1/OE3.

| Key | Historia | Sprint | Status |
|---|---|---|---|
| SW-10 | HU01 - Estudiante consulta dudas por WhatsApp y recibe respuesta automática clara | S2 | Por hacer |
| SW-11 | HU02 - Consultar info del proceso de matrícula (fechas, requisitos, cursos, pagos, inglés) | S2 | Por hacer |
| SW-12 | HU03 - Mensaje de bienvenida en primer contacto con temas que puede consultar | S2 | Por hacer |
| SW-13 | HU04 - Sistema recibe, encola, descarta duplicados y atiende en paralelo | S2 | Por hacer |

### EP02 - Comprensión del Lenguaje e Intenciones (`SW-2`)
> Identificación automática del tema de cada mensaje antes de buscar respuesta. Modulo M2. Objetivos OE1/OE2.

| Key | Historia | Sprint | Status |
|---|---|---|---|
| SW-14 | HU05 - Identificar tema aún con errores ortográficos, abreviaciones o expresiones coloquiales | S2 | Por hacer |
| SW-15 | HU06 - Registrar intención detectada y nivel de certeza por mensaje | S2 | Por hacer |
| SW-16 | HU07 - Admin agrega, edita y elimina frases de ejemplo por intención | S4 | Por hacer |

### EP03 - Base de Conocimiento y Generación de Respuestas (`SW-3`)
> Búsqueda semántica en documentos oficiales y generación de respuestas con IA. Modulo M3. Objetivo OE2.

| Key | Historia | Sprint | Status |
|---|---|---|---|
| SW-17 | HU08 - Respuestas basadas en documentos oficiales de la universidad | S3 | Por hacer |
| SW-18 | HU09 - Continuar consulta y que el chatbot recuerde lo respondido previamente | S3 | Por hacer |
| SW-19 | HU10 - Respuesta honesta cuando no hay información suficiente | S3 | Por hacer |
| SW-20 | HU11 - Buscar fragmentos relevantes considerando contexto activo | S3 | Por hacer |
| SW-21 | HU12 - Admin carga PDFs oficiales desde el sistema web | S3 | Por hacer |
| SW-22 | HU13 - Procesar documentos extrayendo texto y aplicando OCR cuando aplique | S3 | Por hacer |
| SW-23 | HU14 - Eliminar documentos desactualizados borrando contenido indexado | S4 | Por hacer |
| SW-24 | HU15 - Lista de documentos cargados con su estado de procesamiento | S4 | Por hacer |
| SW-42 | HU33 - Script de ingestion que carga documentos públicos UPC 2025-2 | S2 | Por hacer |
| SW-43 | HU34 - Vista de documentos cargados, fragmentos generados y errores | S2 | Por hacer |
| SW-53 | HU45 - PDFs cargados se almacenan en Amazon S3 e indexan desde ahí | S3 | Por hacer |

### EP04 - Procesamiento Confiable e Infraestructura (`SW-4`)
> Atención de mensajes simultáneos con cola de procesamiento, historial 24h y panel de monitoreo interno. Modulo M4. Objetivo OE3.

| Key | Historia | Sprint | Status |
|---|---|---|---|
| SW-25 | HU16 - Chatbot recuerda lo hablado en las últimas 24 horas | S3 | Por hacer |
| SW-26 | HU17 - Mantener historial 24h y recuperarlo desde registro histórico al expirar | S3 | Por hacer |
| SW-27 | HU18 - Levantar entorno completo con un solo comando (BD, cola, workers, HTTPS, migraciones) | S1 | 🟡 En curso |
| SW-28 | HU19 - Panel de monitoreo interno del procesamiento de mensajes | S2 | Por hacer |
| SW-55 | HU47 - Pipeline CI con linting, type check y tests automáticos antes de cada despliegue | S1 | ✅ Finalizada |

### EP05 - Escalado a Humano y Notificaciones (`SW-5`)
> Cuando el chatbot no puede responder con suficiente certeza, deriva a un asesor. Modulo M5. Objetivos OE1/OE4.

| Key | Historia | Sprint | Status |
|---|---|---|---|
| SW-29 | HU20 - Estudiante recibe aviso por WhatsApp cuando su consulta es derivada a asesor | S3 | Por hacer |
| SW-30 | HU21 - Detectar cuando no hay certeza suficiente y registrar conversación como escalada | S3 | Por hacer |
| SW-31 | HU22 - Alerta móvil al admin con número del estudiante y mensaje origen del escalado | S3 | Por hacer |
| SW-32 | HU23 - Distinción visual de conversaciones escaladas en el sistema web | S4 | Por hacer |
| SW-33 | HU24 - Configurar servicio de notificaciones móviles del admin desde el inicio | S1 | Por hacer |

### EP06 - Sistema Web de Administración (`SW-6`)
> Panel web para gestionar conversaciones, responder manualmente, gestionar intenciones, ver métricas y estado del sistema. Modulo M6. Objetivo OE4.

| Key | Historia | Sprint | Status |
|---|---|---|---|
| SW-34 | HU25 - Login admin con correo y contraseña, todas las secciones validan sesión | S1 | Por hacer |
| SW-35 | HU26 - Guardar conversaciones y mensajes con intención detectada y certeza | S3 | Por hacer |
| SW-36 | HU27 - Lista de conversaciones ordenadas por fecha, búsqueda por número o rango | S4 | Por hacer |
| SW-37 | HU28 - Ver hilo completo de conversación estilo WhatsApp en el sistema web | S4 | Por hacer |
| SW-38 | HU29 - Enviar mensaje al estudiante directamente desde el sistema web | S4 | Por hacer |
| SW-39 | HU30 - Cerrar o reabrir conversaciones desde el sistema web | S4 | Por hacer |
| SW-40 | HU31 - Panel de inicio con KPIs del día (activas, escaladas, tema top, certeza) | S4 | Por hacer |
| SW-41 | HU32 - Panel de reportes con filtros por fechas (totales, temas, derivaciones) | S5 | Por hacer |
| SW-54 | HU46 - Gestionar versiones del prompt del chatbot y activar la deseada sin tocar código | S4 | Por hacer |

### EP07 - Atención Personalizada por Perfil del Estudiante (`SW-7`)
> Identifica al estudiante por su número de WhatsApp y carga su perfil académico (carrera, ciclo, turno 2026-1, inglés, créditos). Base de perfiles: 20 estudiantes piloto. Modulo M7. Objetivos OE1/OE3.

| Key | Historia | Sprint | Status |
|---|---|---|---|
| SW-44 | HU35 - Saludo por nombre al estudiante | S4 | Por hacer |
| SW-45 | HU36 - Consultar mi turno de matrícula con fecha y hora exacta | S4 | Por hacer |
| SW-46 | HU37 - Consultar cursos que me corresponden según mi carrera y ciclo | S4 | Por hacer |
| SW-47 | HU38 - Consultar nivel de inglés y avance requerido para egreso | S4 | Por hacer |
| SW-48 | HU39 - Identificar al estudiante por su número y cargar perfil académico | S4 | Por hacer |

### EP08 - Consultas de Facturación y Pagos Pendientes (`SW-8`)
> Consulta de estado de pagos y cuotas del ciclo vigente. Datos de facturación simulados, sin integración con el sistema financiero real. Modulo M8. Objetivos OE1/OE3.

| Key | Historia | Sprint | Status |
|---|---|---|---|
| SW-49 | HU41 - Consultar pagos pendientes del ciclo | S5 | Por hacer |
| SW-50 | HU42 - Consultar monto adeudado y fecha de vencimiento de próxima cuota | S5 | Por hacer |
| SW-51 | HU43 - Identificar consultas de pagos y responder con datos simulados del perfil | S5 | Por hacer |
| SW-52 | HU44 - Admin carga listado simulado de facturación desde el sistema web | S5 | Por hacer |

---

## 3. Mapeo por Sprint

### S1 - Cimientos e Infra · 🟡 active
> **Goal:** Entorno, CI/CD, login admin, push · **Fechas:** 2026-04-15 → 2026-05-01

| Key | Historia | Epic | Status |
|---|---|---|---|
| SW-27 | HU18 - Levantar entorno completo con un solo comando | EP04 Infra | 🟡 En curso |
| SW-33 | HU24 - Configurar servicio de notificaciones móviles del admin | EP05 Escalado | Por hacer |
| SW-34 | HU25 - Login admin con correo y contraseña | EP06 Web Admin | Por hacer |
| SW-55 | HU47 - Pipeline CI con linting, type check y tests | EP04 Infra | ✅ Finalizada |

### S2 - WhatsApp + NLU + Ingesta · 🔵 future
> **Goal:** WhatsApp, intenciones, BC 2025-2 · **Fechas:** 2026-05-04 → 2026-05-22

| Key | Historia | Epic |
|---|---|---|
| SW-10 | HU01 - Estudiante consulta dudas por WhatsApp | EP01 WhatsApp |
| SW-11 | HU02 - Consultar info del proceso de matrícula | EP01 WhatsApp |
| SW-12 | HU03 - Mensaje de bienvenida primer contacto | EP01 WhatsApp |
| SW-13 | HU04 - Recibe, encola, descarta duplicados, atiende en paralelo | EP01 WhatsApp |
| SW-14 | HU05 - Identificar tema con errores/abreviaciones/coloquial | EP02 NLU |
| SW-15 | HU06 - Registrar intención y nivel de certeza | EP02 NLU |
| SW-28 | HU19 - Panel de monitoreo interno | EP04 Infra |
| SW-42 | HU33 - Script de ingestion UPC 2025-2 | EP03 BC |
| SW-43 | HU34 - Vista documentos cargados con fragmentos | EP03 BC |

### S3 - RAG, Memoria y Escalado · 🔵 future
> **Goal:** RAG, contexto, escalado a humano · **Fechas:** 2026-05-25 → 2026-06-12

| Key | Historia | Epic |
|---|---|---|
| SW-17 | HU08 - Respuestas basadas en documentos oficiales | EP03 BC |
| SW-18 | HU09 - Recordar lo respondido previamente | EP03 BC |
| SW-19 | HU10 - Respuesta honesta cuando no hay info | EP03 BC |
| SW-20 | HU11 - Buscar fragmentos considerando contexto | EP03 BC |
| SW-21 | HU12 - Admin carga PDFs desde el sistema web | EP03 BC |
| SW-22 | HU13 - Procesar documentos con OCR cuando aplique | EP03 BC |
| SW-25 | HU16 - Recuerda lo hablado en últimas 24h | EP04 Infra |
| SW-26 | HU17 - Mantener historial 24h + histórico al expirar | EP04 Infra |
| SW-29 | HU20 - Aviso WhatsApp cuando consulta es derivada | EP05 Escalado |
| SW-30 | HU21 - Detectar baja certeza y registrar como escalada | EP05 Escalado |
| SW-31 | HU22 - Alerta móvil al admin con número y mensaje | EP05 Escalado |
| SW-35 | HU26 - Guardar conversaciones y mensajes con intención | EP06 Web Admin |
| SW-53 | HU45 - PDFs en S3 + indexan desde ahí | EP03 BC |

### S4 - Panel Admin + Perfil · 🔵 future
> **Goal:** Panel web y perfil del estudiante · **Fechas:** 2026-06-15 → 2026-06-26

| Key | Historia | Epic |
|---|---|---|
| SW-16 | HU07 - Admin gestiona frases de ejemplo por intención | EP02 NLU |
| SW-23 | HU14 - Eliminar documentos desactualizados | EP03 BC |
| SW-24 | HU15 - Lista documentos con estado | EP03 BC |
| SW-32 | HU23 - Distinción visual conversaciones escaladas | EP05 Escalado |
| SW-36 | HU27 - Lista conversaciones ordenadas y búsqueda | EP06 Web Admin |
| SW-37 | HU28 - Ver hilo completo estilo WhatsApp | EP06 Web Admin |
| SW-38 | HU29 - Enviar mensaje al estudiante desde web | EP06 Web Admin |
| SW-39 | HU30 - Cerrar o reabrir conversaciones | EP06 Web Admin |
| SW-40 | HU31 - Panel inicio con KPIs del día | EP06 Web Admin |
| SW-44 | HU35 - Saludo por nombre al estudiante | EP07 Perfil |
| SW-45 | HU36 - Consultar turno de matrícula | EP07 Perfil |
| SW-46 | HU37 - Consultar cursos que me corresponden | EP07 Perfil |
| SW-47 | HU38 - Consultar nivel de inglés y avance | EP07 Perfil |
| SW-48 | HU39 - Identificar estudiante por número y cargar perfil | EP07 Perfil |
| SW-54 | HU46 - Gestionar versiones del prompt sin tocar código | EP06 Web Admin |

### S5 - Facturación + Reportes · 🔵 future
> **Goal:** Consultas financieras y reportes · **Fechas:** 2026-06-29 → 2026-07-10

| Key | Historia | Epic |
|---|---|---|
| SW-41 | HU32 - Panel de reportes con filtros por fechas | EP06 Web Admin |
| SW-49 | HU41 - Consultar pagos pendientes del ciclo | EP08 Pagos |
| SW-50 | HU42 - Consultar monto adeudado y fecha próxima cuota | EP08 Pagos |
| SW-51 | HU43 - Identificar consultas de pagos | EP08 Pagos |
| SW-52 | HU44 - Admin carga listado simulado facturación | EP08 Pagos |

---

## 4. Matriz Epic × Sprint

| Epic | S1 | S2 | S3 | S4 | S5 | Total |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| EP01 WhatsApp | — | 4 | — | — | — | 4 |
| EP02 NLU | — | 2 | — | 1 | — | 3 |
| EP03 BC + Generación | — | 2 | 7 | 2 | — | 11 |
| EP04 Infra | 2 | 1 | 2 | — | — | 5 |
| EP05 Escalado | 1 | — | 3 | 1 | — | 5 |
| EP06 Web Admin | 1 | — | 1 | 6 | 1 | 9 |
| EP07 Perfil | — | — | — | 5 | — | 5 |
| EP08 Pagos | — | — | — | — | 4 | 4 |
| **Total** | **4** | **9** | **13** | **15** | **5** | **46** |

---

## 5. Notas operativas

- **Numeración HU saltea HU40**: el backlog va HU01-HU39, HU41-HU47 (no existe HU40 en Jira).
- **Sprint 1 vencido**: terminó 2026-05-01 pero sigue activo al 2026-05-08, con 2 historias pendientes (SW-33, SW-34). Cierre y arrastre recomendado.
- **Asignaciones**: solo 2 de 46 historias tienen asignado (Renzo Lenes en SW-27 y SW-55). El resto sin asignar.
- **Desfase con código**: el repo ya entregó en código equivalentes a HU18 (entorno), HU33 (bulk_ingest), HU08/10/11/13 (RAG core), HU12/15 (carga/list docs) — pero en Jira siguen como "Por hacer". Recomendable revisar y mover los completados a "Finalizada" antes de continuar.
- **Source of truth**: este documento es snapshot. Para estado en vivo consultar [Jira board](https://chatbotupc.atlassian.net/jira/software/projects/SW/boards/1).
