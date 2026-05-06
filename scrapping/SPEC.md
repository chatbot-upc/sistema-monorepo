# UPC Web Scraper — Spec del Agente

Eres un desarrollador Python experto en web scraping.
Necesito que construyas un Jupyter Notebook completo para un scraper
del sitio público de la Universidad Peruana de Ciencias Aplicadas (UPC).

## CONTEXTO DEL PROYECTO
Este scraper es el primer paso de un sistema chatbot RAG de atención
al cliente para el proceso de matrícula universitaria. El chatbot
responde preguntas de estudiantes sobre fechas, costos, mallas
curriculares, becas y reglamentos. Para poder responder necesita una
base de conocimiento poblada con documentos oficiales de la UPC.
Este script se encarga de recolectar esos documentos de forma automática
desde el sitio web público de la universidad.

## QUÉ HACE EL SCRAPER
El scraper visita páginas del sitio público de la UPC y hace dos cosas:

1. Si encuentra un enlace a un PDF → lo descarga y lo guarda localmente
2. Si encuentra una página HTML con texto relevante sobre matrícula,
   becas, mallas, reglamentos o calendarios → extrae el texto limpio
   y lo guarda como archivo .txt

El scraper parte de URLs semilla conocidas y desde cada una sigue los
links internos hasta 3 niveles de profundidad, siempre dentro del
dominio *.upc.edu.pe. No indexa ni procesa los documentos — solo los
recolecta y organiza en carpetas locales para que otro pipeline los
procese después.

## COMPORTAMIENTO DETALLADO

Cuando llega a una URL el scraper hace lo siguiente:

### Paso 1 — Intentar con requests simple (rápido, sin navegador)
- Si el HTML resultante tiene más de 500 palabras visibles → usar ese HTML
- Si tiene menos de 500 palabras → la página usa JavaScript, pasar al Paso 2

### Paso 2 — Reintentar con Playwright (navegador headless)
- Renderiza la página completa incluyendo contenido dinámico
- Espera a que el DOM esté completamente cargado
- Intenta hacer click en botones que contengan texto como:
  "Ver malla", "Descargar", "Ver reglamento", "Ver documento",
  "Ver plan de estudios" para capturar PDFs que se cargan dinámicamente

### Paso 3 — Extraer links de la página
- Recopilar todos los `<a href>` de la página renderizada
- Por cada link:
  - ¿Termina en `.pdf`? → encolar para descarga
  - ¿Es una URL interna de `*.upc.edu.pe`? → encolar para visitar
    si no fue visitada antes y está dentro del límite de profundidad
  - ¿Contiene patrones de login o redes sociales? → ignorar
  - ¿Es externo? → ignorar

### Paso 4 — Decidir si la página HTML vale la pena guardar
- Extraer solo el texto del contenido principal
  (ignorar nav, header, footer, sidebar, scripts, estilos)
- Si el texto tiene más de 300 caracteres Y contiene al menos una
  keyword relevante → guardar como .txt
- Keywords: matrícula, matricula, horario, cronograma, calendario,
  malla, currícula, reglamento, beca, financiamiento, pago, pensión,
  requisito, ciclo, crédito, egreso, ingresante, grado, titulación

### Paso 5 — Delay entre requests
- Esperar entre 2 y 4 segundos de forma aleatoria antes del
  siguiente request para no sobrecargar el servidor ni ser bloqueado

## URLS SEMILLA (punto de partida)
- https://pregrado.upc.edu.pe/facultad-de-ingenieria/ingenieria-de-sistemas-de-informacion/
- https://pregrado.upc.edu.pe/facultad-de-ingenieria/
- https://www.upc.edu.pe/admision/becas-y-financiamiento/becas-internas-alumnos/
- https://www.upc.edu.pe/admision/becas-y-financiamiento/
- https://explora.upc.edu.pe/
- https://www.upc.edu.pe/estudia-con-nosotros/matricula/
- https://www.upc.edu.pe/estudia-con-nosotros/calendario-academico/

## REGLAS GENERALES
- Solo dominio `*.upc.edu.pe`, no seguir links externos
- Máximo 3 niveles de profundidad desde cada URL semilla
- No visitar la misma URL dos veces (control de visitados)
- Saltar URLs con: `login`, `signin`, `campus-net`, `intranet`, `blackboard`,
  `canvas`, `aula-virtual`, `facebook`, `twitter`, `instagram`, `youtube`,
  `linkedin`, `mailto:`, `javascript:`, `#`
- Si una página da error HTTP o timeout → registrar en el log y continuar
- No reintentar más de una vez por URL

## ESTRUCTURA DE CARPETAS DE SALIDA

```
upc_documents/
  pdfs/
    pregrado/       ← PDFs de mallas y planes de estudio
    becas/          ← PDFs de becas y financiamiento
    matricula/      ← PDFs de proceso de matrícula
    reglamentos/    ← Reglamentos académicos
    otros/          ← PDFs de secciones no clasificadas
  html_text/
    pregrado/
    becas/
    matricula/
    reglamentos/
    otros/
  log_scraping.csv
```

La subcarpeta se elige por la sección de la URL:
- `pregrado.upc.edu.pe/*` → `pregrado/`
- `*/becas*` → `becas/`
- `*/matricula*` → `matricula/`
- `*/reglamento*` → `reglamentos/`
- todo lo demás → `otros/`

## LOG CSV — una fila por cada URL procesada
Columnas: `fecha_hora`, `url`, `profundidad`, `tipo` (pdf/html/ignorada/error),
`archivo_guardado`, `palabras_extraidas`, `notas`

## ESTRUCTURA DEL NOTEBOOK

**Celda 1**: Instalación de dependencias (crawl4ai, beautifulsoup4,
requests, aiofiles, nest_asyncio)
Incluir: `!crawl4ai-setup` para instalar Playwright

**Celda 2**: Imports y configuración global
Todo lo editable en un solo lugar: URLs semilla, profundidad, delay,
carpetas, keywords, patrones a saltar

**Celda 3**: Funciones auxiliares
- validar dominio permitido
- detectar subcarpeta por URL
- limpiar HTML y extraer texto principal
- generar nombre de archivo único desde URL
- escribir fila en el CSV de log

**Celda 4**: Función `fetch_simple(url)`
Descarga con requests, retorna HTML y cantidad de palabras visibles

**Celda 5**: Función `fetch_playwright(url)`
Usa crawl4ai + Playwright, renderiza JS, intenta clicks en botones de
descarga, retorna HTML renderizado

**Celda 6**: Función `fetch_smart(url)`
Orquesta: intenta simple primero, cae a Playwright si hay poco texto,
retorna HTML final y método usado

**Celda 7**: Función `process_page(url, depth, visited)`
Lógica completa de una página: fetch → extraer links → clasificar links
→ guardar si es útil → encolar links hijos

**Celda 8**: Función `download_pdf(url, subfolder)`
Descarga un PDF con requests, lo guarda en la subcarpeta correcta,
registra en log

**Celda 9**: Función `crawl(seed_urls)`
Orquesta el crawling completo con cola BFS, control de visitados,
límite de profundidad y delay entre requests.
Muestra progreso en tiempo real: URLs visitadas, PDFs descargados,
páginas guardadas

**Celda 10**: Ejecución
Llama a `crawl(SEED_URLS)` y muestra barra de progreso con tqdm

**Celda 11**: Resumen de resultados
Lee el log CSV y muestra:
- Total de URLs visitadas
- Total de PDFs descargados con sus nombres y tamaños
- Total de páginas HTML guardadas
- URLs que dieron error
- Distribución por subcarpeta
- Tabla resumen con pandas
