# Limpieza del backlog de historias de usuario

**Fecha:** 2026-09-12
**Estado:** Aprobado, pendiente de plan de implementación

## Contexto

El backlog de la tesis vive en `HU_y_Criterios_de_Aceptacion_Chatbot_RAG.xlsx`
(plantilla de la universidad, 4 hojas: `EPICAS`, `HIstoria de Usuario`,
`Instructivo`, `Ejemplo`). Contiene **46 historias** numeradas HU01–HU47 — con un
hueco: HU40 no existe — repartidas en 8 épicas, cada una con 2 criterios de
aceptación, para un total de 92 criterios.

Ese archivo es la fuente de trazabilidad del anexo de pruebas: los casos de prueba
declaran contra qué HU y qué criterio se ejecutan.

## Problema

El backlog mezcla historias de usuario con tareas técnicas, y eso contamina la
trazabilidad del anexo.

**Seis historias no son historias de usuario.** Cinco declaran el rol
«Desarrollador» y una disfraza una decisión de arquitectura como necesidad del
administrador:

| ID | Historia | Naturaleza real |
|---|---|---|
| HU18 | Levantar el entorno con un comando | Tarea de desarrollo |
| HU19 | Panel de monitoreo interno | Herramienta del equipo |
| HU24 | Configurar el servicio de notificaciones móviles | Configuración técnica |
| HU33 | Script de ingestión inicial | Tarea de despliegue |
| HU45 | Almacenar los PDFs en Amazon S3 | Decisión de arquitectura |
| HU47 | Pipeline de CI con linting, tipos y tests | Práctica de ingeniería |

Ninguna la valida un usuario del producto y ninguna se prueba como funcionalidad.
El Excel de casos de prueba ya las excluía bajo el rótulo «fuera de alcance», lo
que confirma el diagnóstico: si no generan casos, no pertenecen al backlog
funcional.

**Nueve historias declaran el rol «Sistema».** «Como Sistema quiero…» tampoco
identifica a un usuario. A diferencia de las anteriores, estas sí encierran valor
real para un usuario concreto: la propia columna «Razón» de cada una nombra a quien
recibe el beneficio. El defecto está en el enunciado, no en el contenido.

**El hueco de HU40** deja la numeración con un salto sin explicación.

## Decisiones

Tomadas durante el diseño, con su motivo:

1. **Se eliminan las 6 historias técnicas**, no se reubican en una sección aparte.
   El backlog queda como backlog de producto; el trabajo técnico ya está
   registrado en Jira y en el repositorio.
2. **Se renumera cerrando huecos**, conservando el orden relativo. Con 6 bajas y el
   hueco preexistente de HU40, el resultado es HU01–HU40 corrido.
3. **Las 9 historias de rol «Sistema» se reescriben hacia el usuario que recibe el
   valor**, que no siempre es el estudiante: cuatro tienen al administrador como
   beneficiario según su propia «Razón». Forzarlas todas al estudiante sustituiría
   una atribución falsa por otra.
4. **Jira no se modifica.** Sus 46 tickets `SW-xx` llevan el ID anterior en el
   título y quedan como registro histórico del desarrollo. El Excel es la fuente
   para la tesis.
5. **Se edita el archivo existente en vez de generarlo desde cero.** La plantilla
   de la universidad tiene celdas combinadas, encabezados de dos niveles y estilos
   que el entregable debe conservar. Reproducirlos desde un generador cuesta más de
   lo que aporta para un cambio acotado.

## Diseño

### Renumeración

HU01–HU17 conservan su identificador. Las 23 restantes se desplazan:

| Antes | Ahora | Antes | Ahora | Antes | Ahora |
|---|---|---|---|---|---|
| HU01–HU17 | HU01–HU17 | HU29 | HU26 | HU38 | HU34 |
| HU20 | HU18 | HU30 | HU27 | HU39 | HU35 |
| HU21 | HU19 | HU31 | HU28 | HU41 | HU36 |
| HU22 | HU20 | HU32 | HU29 | HU42 | HU37 |
| HU23 | HU21 | HU34 | HU30 | HU43 | HU38 |
| HU25 | HU22 | HU35 | HU31 | HU44 | HU39 |
| HU26 | HU23 | HU36 | HU32 | HU46 | HU40 |
| HU27 | HU24 | HU37 | HU33 | | |
| HU28 | HU25 | | | | |

Los identificadores de criterio siguen a su historia: `HU25-2` pasa a `HU22-2`.

Resultado: **40 historias, 80 criterios de aceptación**, sin huecos.

### Enunciados reescritos

Cada uno reemplaza las columnas `Rol`, `Característica / Funcionalidad`,
`Razón / Resultado` y `REDACCION`. La columna `REDACCION` se deriva siempre como
`Como {rol} quiero {característica} para {razón}`.

**Rol: Estudiante universitario**

| ID (antes) | Necesito | Con la finalidad de |
|---|---|---|
| HU04 (HU04) | que mi consulta se atienda aunque varios estudiantes escriban al mismo tiempo y aunque WhatsApp entregue mi mensaje más de una vez | recibir una sola respuesta y no quedarme esperando porque el sistema esté atendiendo a otro |
| HU11 (HU11) | que el chatbot busque en los documentos oficiales tomando en cuenta lo que ya venimos conversando | que su respuesta se refiera a mi consulta real y no a otro tema parecido |
| HU17 (HU17) | que el chatbot recupere lo que hablamos aunque haya pasado más de un día desde mi último mensaje | retomar mi consulta sin volver a explicar todo desde cero |
| HU35 (HU39) | que el chatbot me reconozca por mi número de WhatsApp sin que yo tenga que escribir mi carrera, ciclo ni código | recibir respuestas que consideren mi situación académica real desde el primer mensaje |
| HU38 (HU43) | que el chatbot entienda cuando le pregunto por mis pagos, aunque lo diga de distintas formas | recibir el estado de mis cuotas y no una explicación general de medios de pago |

**Rol: Administrador del sistema**

| ID (antes) | Necesito | Con la finalidad de |
|---|---|---|
| HU06 (HU06) | consultar la intención detectada y el nivel de certeza de cada mensaje del estudiante | monitorear la calidad de la clasificación e identificar los temas donde el chatbot se equivoca |
| HU13 (HU13) | que los documentos que cargo se procesen automáticamente, incluidos los escaneados o en imagen | no transcribir nada a mano y que su contenido quede disponible para el chatbot |
| HU19 (HU21) | que las conversaciones donde el chatbot no entendió la consulta con suficiente certeza queden registradas como escaladas | identificarlas y priorizarlas sin revisar una por una |
| HU23 (HU26) | que cada conversación y sus mensajes queden guardados con la intención detectada y su certeza | revisar el historial completo desde el sistema web y que los indicadores de uso sean calculables |

Los 18 criterios de aceptación de estas nueve historias **no cambian de contenido**;
solo se renumeran los que arrastran cambio de identificador. Se verificó uno a uno
que cada criterio sigue siendo coherente con el enunciado nuevo.

Queda fuera de este trabajo, señalado para una posible segunda pasada: dos títulos
de criterio conservan lenguaje interno (`HU17-1 Historial reciente disponible en
memoria`, `HU17-2 Historial reciente expirado`).

### Hoja EPICAS

Se mantienen las 8 épicas. Composición resultante:

| Épica | Historias | Total |
|---|---|---|
| EP01 | HU01–HU04 | 4 |
| EP02 | HU05–HU07 | 3 |
| EP03 | HU08–HU15, HU30 | 9 |
| EP04 | HU16, HU17 | 2 |
| EP05 | HU18–HU21 | 4 |
| EP06 | HU22–HU29, HU40 | 9 |
| EP07 | HU31–HU35 | 5 |
| EP08 | HU36–HU39 | 4 |
| | | **40** |

Dos objetivos de épica quedan desactualizados por las bajas y se reescriben:

- **EP03** menciona que la base de conocimiento «se puebla inicialmente mediante un
  script de ingestión con documentos públicos de la UPC del ciclo 2025-2». Ese
  script era HU33. El objetivo pasa a describir únicamente la carga y actualización
  manual por parte del administrador, que es lo que permanece como historia.
- **EP04** se titula «Procesamiento Confiable e Infraestructura» y su objetivo cita
  la cola de procesamiento y el panel de monitoreo interno. La cola pertenece a HU04
  (EP01) y el monitoreo se eliminó. Pasa a:

  > **EP04 — Continuidad de la Conversación.** El chatbot conserva el contexto de
  > cada conversación durante 24 horas y lo recupera del registro histórico cuando
  > ha expirado, para que el estudiante retome su consulta sin repetir lo que ya
  > contó.

Disolver EP04 y repartir HU16/HU17 en otras épicas se descartó: es un cambio
estructural mayor sin ganancia para el lector.

### Hoja MAPEO (nueva)

Deja constancia del cambio de numeración dentro del propio archivo, para quien
compare con la versión anterior del documento y para reconstruir después el Excel
de casos de prueba. Dos bloques:

1. **Historias conservadas** — ID anterior, ID nuevo, título.
2. **Historias eliminadas** — ID anterior, título, motivo de la baja.

### Script

`tools/fix_backlog_xlsx.py`, versionado en el repositorio para que la
transformación sea auditable y repetible.

- **Entrada:** `docs/HU_y_Criterios_de_Aceptacion_Chatbot_RAG_v1.xlsx`. El archivo
  original se copia primero desde `~/Downloads` al repositorio, para que la
  transformación tenga una línea base versionada y reproducible. El script lo abre
  en solo lectura y nunca lo modifica.
- **Salida:** `docs/HU_y_Criterios_de_Aceptacion_Chatbot_RAG_v2.xlsx`.
- **Datos:** las 40 historias con su rol, enunciado y criterios viven como
  estructura de datos dentro del script. Los enunciados de las 31 historias no
  reescritas se leen del archivo original; solo los 9 reescritos y los objetivos de
  EP03/EP04 están literales en el script.

**Estrategia de edición.** La hoja `HIstoria de Usuario` tiene una estructura
regular de **3 filas por historia** (escenario 1, escenario 2, fila separadora) con
celdas combinadas verticalmente en las columnas de enunciado. El script **no borra
filas intermedias**: `openpyxl` no reajusta los rangos combinados al desplazar
filas, y hacerlo rompería el formato de la plantilla.

En su lugar:

1. Reescribe los valores en sitio, conservando el bloque de 3 filas por historia.
2. Al terminar, elimina únicamente las filas sobrantes de la cola (las 6 historias
   de más), donde no hay contenido debajo que desplazar.

Mismo criterio en `EPICAS`. Las hojas `Instructivo` y `Ejemplo` no se abren para
escritura.

### Verificación

El script valida antes de escribir el archivo y aborta si algo no cuadra:

- 40 historias con identificadores HU01–HU40, correlativos y sin repetidos.
- 80 criterios de aceptación; cada historia con exactamente 2 escenarios.
- Ningún rol igual a «Sistema» ni «Desarrollador».
- Ninguna de las 6 historias eliminadas presente en ninguna hoja.
- Suma de historias por épica en `EPICAS` igual a 40, y cada ID referenciado en
  `EPICAS` existente en la hoja de historias.
- Hojas `Instructivo` y `Ejemplo` con el mismo contenido celda a celda que el
  original.

## Consecuencias

- **El Excel de casos de prueba queda obsoleto.** Sus 87 casos apuntan a los
  identificadores anteriores. Se reconstruye en un trabajo aparte, trazando contra
  esta numeración y usando la hoja `MAPEO` como referencia.
- **Jira queda desincronizado** por decisión explícita. Sus tickets conservan la
  numeración del desarrollo.
- **La documentación del repositorio que cita IDs de HU** (`docs/JIRA_MAPPING.md`,
  mensajes de commit históricos) mantiene la numeración anterior. No se reescribe:
  refleja el estado del proyecto cuando se produjo.

## Fuera de alcance

- Reescribir los títulos de criterios que usan lenguaje interno.
- Reconstruir el Excel de casos de prueba.
- Modificar Jira, `docs/JIRA_MAPPING.md` o el historial de commits.
- Cualquier cambio en el código de la aplicación.
