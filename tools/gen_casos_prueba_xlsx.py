#!/usr/bin/env python3
"""Plan de ejecución de casos de prueba v2 (spec 2026-09-12).

Parte del Excel de casos original (87 casos) y produce la versión de ejecución:

1. Reescribe la trazabilidad a la numeración nueva del backlog (HU01-HU40).
   49 de los 87 casos cambian de criterio; 38 lo conservan.
2. Precarga el estado inicial de cada caso según la revisión estática de código,
   para que el ejecutor sepa qué esperar antes de abrirlo.
3. Añade a cada hoja una columna "Resultado obtenido" y un bloque de registro de
   ejecución en blanco.
4. Añade las hojas RESUMEN, GLOSARIO (tomada del refinamiento previo) y MAPEO.

Ningún caso se elimina: un caso que va a fallar produce la evidencia del defecto.

Se edita una copia del original en vez de generar las hojas desde cero, para
conservar exactamente la plantilla: anchos, alturas, bordes, rellenos y
combinaciones. Por eso el script nunca inserta ni borra filas; solo escribe en
celdas existentes, extiende las combinaciones a la columna nueva y usa las filas
libres bajo las postcondiciones para el bloque de ejecución.

Uso:
    uv run --no-project --with openpyxl python tools/gen_casos_prueba_xlsx.py
"""

from __future__ import annotations

import re
import shutil
import sys
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "Casos_de_Prueba_Chatbot_RAG_v1.xlsx"
SRC_GLOSARIO = ROOT / "docs" / "Casos_de_Prueba_Chatbot_RAG_glosario.xlsx"
DST = ROOT / "docs" / "Casos_de_Prueba_Chatbot_RAG_v2.xlsx"

SHEET_INDEX = "LISTA CP"

# Layout de una hoja de caso (idéntico en las 87).
ROW_TITLE, ROW_AUTOR, ROW_PRECOND = 1, 3, 3
ROW_STEP_HEADER, ROW_STEP_FIRST, ROW_STEP_LAST = 6, 7, 18
ROW_HU, ROW_POSTCOND = 19, 20
COL_RESULTADO = 5  # columna nueva
EXEC_FIRST_ROW = 24  # bajo el bloque combinado de postcondiciones (20-22)

HEADER_FILL = "FFF2AC84"  # el mismo naranja del título en la plantilla

# Layout de la hoja índice.
IDX_FIRST_ROW, IDX_LAST_ROW = 3, 89
IDX_COL_CP, IDX_COL_DESC, IDX_COL_HU, IDX_COL_ESC, IDX_COL_CRIT = 2, 3, 4, 5, 6
IDX_COL_ESTADO, IDX_COL_FINAL = 7, 8
IDX_NOTES_FIRST = 92

# ── Backlog: renumeración aplicada en el spec del mismo día ───────────────

REMOVED_HU = {18, 19, 24, 33, 45, 47}
_KEPT_HU = [n for n in [*range(1, 40), *range(41, 48)] if n not in REMOVED_HU]
RENUMBER = {f"HU{o:02d}": f"HU{i:02d}" for i, o in enumerate(_KEPT_HU, start=1)}

# ── Veredictos de la revisión estática (informe 2026-09-12, commit 6c2a676) ──

ESTADO_LISTO = "Listo"
ESTADO_KB = "Bloqueado — falta KB"
ESTADO_FALLO = "Fallo esperado"
ESTADO_RIESGO = "Riesgo — cumple parcial"
ESTADO_NA = "No ejecutable"

# Casos que la revisión da por fallidos, con el motivo que se anota en las
# precondiciones para que el ejecutor sepa qué está documentando.
FALLO: dict[str, str] = {
    "CP011": "el worker corre con --pool=solo y una sola réplica, sin concurrencia",
    "CP015": "el respaldo por modelo persiste certeza 1,0 en lugar del valor real",
    "CP020": "la recuperación no pondera vigencia ni fecha de publicación",
    "CP028": "la API no valida el tipo de archivo antes de crear el documento",
    "CP038": "el respaldo en base de datos usa la misma ventana de 24 h que el caché",
    "CP041": "no existe regla de escalado por umbral de certeza",
    "CP042": "no existe regla de escalado por umbral de certeza",
    "CP048": "falta el middleware de sesión: las rutas no redirigen al inicio de sesión",
    "CP050": "la cola no reintenta ni conserva el evento ante un fallo de base de datos",
    "CP051": "el filtro por teléfono compara contra el nombre del contacto",
    "CP052": "el listado de conversaciones no expone filtro de fechas",
    "CP054": "el hilo carga una sola página de 100 mensajes, sin paginación",
    "CP061": "activas y escaladas son conteos globales de estado, no del día",
    "CP063": "la exportación entrega indicadores agregados, no el registro de conversaciones",
}

# Casos que cumplen el escenario pero fallan un detalle del control.
RIESGO: dict[str, str] = {
    "CP008": "la bienvenida anuncia becas, tema ajeno al catálogo de este caso",
    "CP010": "la deduplicación ocurre en el worker; el webhook encola una tarea por entrega",
    "CP014": "la certeza se guarda por conversación, no ligada al mensaje",
    "CP026": "la consulta de búsqueda la redacta el modelo; no hay reescritura determinista",
    "CP049": "la certeza se guarda por conversación, no ligada al mensaje",
    "CP056": "el fallo de envío llega como error genérico, sin la causa del proveedor",
    "CP057": "el fallo de envío llega como error genérico, sin la causa del proveedor",
    "CP060": "activas y escaladas no están acotadas al día",
    "CP066": "la bienvenida inicial es genérica; el nombre aparece en la respuesta siguiente",
    "CP069": "no hay instrucción explícita de responder que el turno no se ha publicado",
    "CP073": "el requisito de inglés está fijo en 5 niveles para todas las carreras",
    "CP074": "el requisito de inglés está fijo en 5 niveles para todas las carreras",
    "CP077": "la agregación de facturación no filtra por ciclo",
    "CP079": "el formato de moneda usa separadores en inglés (S/ 1,250.50)",
    "CP082": "depende de que el clasificador resuelva el mensaje mixto a consulta de pagos",
}

NO_EJECUTABLE = {
    "CP087": "no existe la acción de desactivar un prompt; la protección la garantiza el diseño"
}

# Documentos que hay que indexar antes de poder ejecutar el caso.
FALTA_KB: dict[str, str] = {
    "CP001": "D-FEC",
    "CP002": "D-REQ",
    "CP003": "D-FEC",
    "CP004": "D-REQ",
    "CP006": "D-PAG",
    "CP007": "D-ING",
    "CP019": "D-REQ",
    "CP021": "D-REQ",
    "CP022": "D-FEC y D-ING",
    "CP025": "D-REQ",
    "CP026": "D-REQ",
    "CP035": "D-REQ",
    "CP036": "D-REQ",
    "CP037": "D-REQ",
}

EXEC_FIELDS = [
    "Estado final (Aprobado / Fallido / Bloqueado / No ejecutado):",
    "Fecha de ejecución:",
    "Ejecutor:",
    "Evidencia (captura, registro o enlace):",
    "Defecto asociado:",
    "Observaciones:",
]

NOTAS_INDICE = [
    "(*) La columna de historia y criterio usa la numeración del backlog depurado "
    "(HU01-HU40). Ver la hoja MAPEO para la equivalencia con la numeración anterior.",
    "NOTA: Hay una hoja por cada caso. El nombre de cada pestaña coincide con su "
    "identificador en este listado. Cada hoja incluye una columna «Resultado "
    "obtenido» y un bloque «Registro de ejecución» en blanco.",
    "Cobertura: 87 casos para las 40 historias y los 80 criterios del backlog. "
    "Cobertura completa: no hay historia ni criterio sin caso asociado.",
    "Estado inicial: lo precarga la revisión estática de código del 2026-09-12 "
    "(rama development, commit 6c2a676) e indica qué esperar antes de ejecutar. "
    "No sustituye al resultado real: el estado final lo escribe el ejecutor.",
    "«Fallo esperado» y «Riesgo — cumple parcial» se ejecutan igual: su valor es "
    "documentar el defecto con evidencia, no confirmarlo por lectura de código.",
    "«Bloqueado — falta KB» requiere indexar antes los documentos oficiales que "
    "indica su precondición. Sin ese contenido el caso falla por falta de datos, "
    "no por defecto del sistema.",
    "Datos de control: WA_A, WA_B y WA_NUEVO son alias de líneas autorizadas de QA. "
    "Ana, Bruno, fechas, cuotas y montos explícitos son datos sintéticos; preparar "
    "cada caso de forma independiente.",
    "Referencias documentales: D-FEC, D-REQ, D-CUR, D-PAG, D-ING y D-MALLA son "
    "alias propuestos al redactar los casos, no nombres de archivo confirmados. Su "
    "significado está en la hoja GLOSARIO.",
    "Parámetros por completar antes de ejecutar: URL y credenciales del entorno de "
    "QA, esquema de importación de facturación, y definición aprobada de «activas» "
    "y de la tasa de derivación.",
    "Alcance temporal: los perfiles de matrícula contemplan 2026-1 según EP07. Los "
    "relojes y periodos explícitos de otros conjuntos de datos sirven para pruebas "
    "controladas.",
]


def estado_de(cp: str) -> str:
    if cp in NO_EJECUTABLE:
        return ESTADO_NA
    if cp in FALLO:
        return ESTADO_FALLO
    if cp in RIESGO:
        return ESTADO_RIESGO
    if cp in FALTA_KB:
        return ESTADO_KB
    return ESTADO_LISTO


def nota_precondicion(cp: str) -> str:
    """Prefijo que se antepone a las precondiciones del caso. Vacío si está listo."""
    partes: list[str] = []
    if cp in FALTA_KB:
        partes.append(
            f"Bloqueado: indexar {FALTA_KB[cp]} en la base de conocimiento antes de "
            "ejecutar."
        )
    if cp in FALLO:
        partes.append(
            f"Fallo esperado según la revisión de código del 2026-09-12: "
            f"{FALLO[cp]}. Ejecutar igualmente y registrar la evidencia del defecto."
        )
    if cp in RIESGO:
        partes.append(f"Riesgo conocido: {RIESGO[cp]}.")
    if cp in NO_EJECUTABLE:
        partes.append(f"No ejecutable: {NO_EJECUTABLE[cp]}.")
    return " ".join(partes)


# ── Escritura ─────────────────────────────────────────────────────────────


def remap_hu_line(text: str) -> tuple[str, str, str]:
    """Reescribe «HU relacionada: HU20. Escenario 1. Criterio HU20-1.».

    Devuelve (línea nueva, HU nueva, criterio nuevo).
    """
    m = re.search(r"(HU\d+)\.\s*Escenario\s*(\d+)", text)
    if not m:
        raise ValueError(f"No se pudo interpretar la trazabilidad: {text!r}")
    old, esc = m.group(1), m.group(2)
    new = RENUMBER[old]
    line = f"HU relacionada: {new}. Escenario {esc}. Criterio {new}-{esc}."
    return line, new, f"{new}-{esc}"


def widen_merges(ws: Worksheet) -> None:
    """Extiende a la columna nueva las combinaciones que llegaban hasta la D."""
    for rng in list(ws.merged_cells.ranges):
        if rng.max_col == COL_RESULTADO - 1 and rng.min_col == 1:
            ws.unmerge_cells(str(rng))
            ws.merge_cells(
                start_row=rng.min_row,
                start_column=1,
                end_row=rng.max_row,
                end_column=COL_RESULTADO,
            )
        elif rng.max_col == COL_RESULTADO - 1 and rng.min_col == 2:
            ws.unmerge_cells(str(rng))
            ws.merge_cells(
                start_row=rng.min_row,
                start_column=2,
                end_row=rng.max_row,
                end_column=COL_RESULTADO,
            )


def add_resultado_column(ws: Worksheet) -> None:
    """Columna «Resultado obtenido», clonando el estilo de la columna vecina."""
    header_src = ws.cell(ROW_STEP_HEADER, COL_RESULTADO - 1)
    header = ws.cell(ROW_STEP_HEADER, COL_RESULTADO)
    header.value = "Resultado obtenido"
    header.font = copy(header_src.font)
    header.fill = copy(header_src.fill)
    header.border = copy(header_src.border)
    header.alignment = copy(header_src.alignment)

    for row in range(ROW_STEP_FIRST, ROW_STEP_LAST + 1):
        src = ws.cell(row, COL_RESULTADO - 1)
        dst = ws.cell(row, COL_RESULTADO)
        dst.border = copy(src.border)
        dst.alignment = copy(src.alignment)
        dst.font = copy(src.font)

    ws.column_dimensions[get_column_letter(COL_RESULTADO)].width = 46.0


def add_exec_block(ws: Worksheet, estado: str) -> None:
    """Bloque «Registro de ejecución» en las filas libres bajo postcondiciones."""
    row = EXEC_FIRST_ROW
    ws.merge_cells(
        start_row=row, start_column=1, end_row=row, end_column=COL_RESULTADO
    )
    head = ws.cell(row, 1)
    head.value = "REGISTRO DE EJECUCIÓN"
    head.fill = PatternFill("solid", fgColor=HEADER_FILL)
    head.font = Font(sz=11, b=True)
    head.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 25.0

    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    ws.merge_cells(
        start_row=row, start_column=3, end_row=row, end_column=COL_RESULTADO
    )
    label = ws.cell(row, 1)
    label.value = "Estado inicial (revisión de código, no editar):"
    label.font = Font(sz=10, b=True)
    label.alignment = Alignment(vertical="center", wrap_text=True)
    ws.cell(row, 3).value = estado
    ws.cell(row, 3).alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 21.0

    for field in EXEC_FIELDS:
        row += 1
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        ws.merge_cells(
            start_row=row, start_column=3, end_row=row, end_column=COL_RESULTADO
        )
        cell = ws.cell(row, 1)
        cell.value = field
        cell.font = Font(sz=10)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.cell(row, 3).alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[row].height = 21.0


def process_case(ws: Worksheet, cp: str) -> tuple[str, str]:
    """Aplica los cambios a una hoja de caso. Devuelve (HU nueva, criterio nuevo)."""
    line, hu, crit = remap_hu_line(str(ws.cell(ROW_HU, 1).value or ""))
    ws.cell(ROW_HU, 1).value = line

    nota = nota_precondicion(cp)
    if nota:
        actual = str(ws.cell(ROW_PRECOND, 1).value or "")
        ws.cell(ROW_PRECOND, 1).value = f"{nota} {actual}"

    widen_merges(ws)
    add_resultado_column(ws)
    add_exec_block(ws, estado_de(cp))
    return hu, crit


def update_index(ws: Worksheet, traza: dict[str, tuple[str, str]]) -> None:
    """Actualiza la hoja índice: HU nueva, estado inicial y columna de resultado."""
    for col, (title, width) in enumerate(
        (("Estado inicial", 26.0), ("Estado final", 20.0)), start=IDX_COL_ESTADO
    ):
        header_src = ws.cell(2, IDX_COL_CRIT)
        cell = ws.cell(2, col)
        cell.value = title
        cell.font = copy(header_src.font)
        cell.fill = copy(header_src.fill)
        cell.border = copy(header_src.border)
        cell.alignment = copy(header_src.alignment)
        ws.column_dimensions[get_column_letter(col)].width = width

    for row in range(IDX_FIRST_ROW, IDX_LAST_ROW + 1):
        cp = str(ws.cell(row, IDX_COL_CP).value or "").strip()
        if not cp:
            continue
        hu, _crit = traza[cp]
        ws.cell(row, IDX_COL_HU).value = hu
        for col in (IDX_COL_ESTADO, IDX_COL_FINAL):
            src = ws.cell(row, IDX_COL_CRIT)
            cell = ws.cell(row, col)
            cell.border = copy(src.border)
            cell.alignment = copy(src.alignment)
            cell.font = copy(src.font)
        ws.cell(row, IDX_COL_ESTADO).value = estado_de(cp)

    # Las notas al pie: se reescriben y sus combinaciones se extienden a la H.
    for rng in list(ws.merged_cells.ranges):
        if rng.min_row >= IDX_NOTES_FIRST:
            ws.unmerge_cells(str(rng))
    row = IDX_NOTES_FIRST
    for nota in NOTAS_INDICE:
        ws.cell(row, IDX_COL_CP).value = nota
        ws.cell(row, IDX_COL_CP).alignment = Alignment(vertical="center", wrap_text=True)
        ws.merge_cells(
            start_row=row, start_column=IDX_COL_CP, end_row=row, end_column=IDX_COL_FINAL
        )
        row += 1
    while row <= ws.max_row:
        for col in range(IDX_COL_CP, IDX_COL_FINAL + 1):
            ws.cell(row, col).value = None
        row += 1


def add_resumen(wb, traza: dict[str, tuple[str, str]]) -> None:
    ws = wb.create_sheet("RESUMEN", 1)
    counts: dict[str, int] = {}
    for cp in traza:
        counts[estado_de(cp)] = counts.get(estado_de(cp), 0) + 1

    hus = {hu for hu, _ in traza.values()}
    crits = {crit for _, crit in traza.values()}

    rows: list[tuple[str, object]] = [
        ("RESUMEN DEL PLAN DE EJECUCIÓN", ""),
        ("", ""),
        ("Casos de prueba", len(traza)),
        ("Historias cubiertas", f"{len(hus)} de 40"),
        ("Criterios cubiertos", f"{len(crits)} de 80"),
        ("", ""),
        ("Estado inicial (revisión de código del 2026-09-12)", ""),
        (ESTADO_LISTO, counts.get(ESTADO_LISTO, 0)),
        (ESTADO_KB, counts.get(ESTADO_KB, 0)),
        (ESTADO_FALLO, counts.get(ESTADO_FALLO, 0)),
        (ESTADO_RIESGO, counts.get(ESTADO_RIESGO, 0)),
        (ESTADO_NA, counts.get(ESTADO_NA, 0)),
        ("", ""),
        (
            "El estado inicial indica qué esperar, no un resultado. Todos los casos "
            "se ejecutan salvo el marcado «No ejecutable»; los bloqueados, después "
            "de indexar los documentos que indica su precondición.",
            "",
        ),
    ]
    for label, value in rows:
        ws.append([label, value])
    ws["A1"].font = Font(sz=12, b=True)
    ws["A7"].font = Font(sz=11, b=True)
    ws.column_dimensions["A"].width = 62.0
    ws.column_dimensions["B"].width = 16.0
    ws["A14"].alignment = Alignment(wrap_text=True, vertical="top")


def add_glosario(wb, src_path: Path) -> None:
    """Copia la hoja GLOSARIO del refinamiento previo, celda a celda."""
    if not src_path.exists():
        print(f"  aviso: no se encontró {src_path.name}, se omite GLOSARIO")
        return
    src = load_workbook(src_path)["GLOSARIO"]
    ws = wb.create_sheet("GLOSARIO")
    for row in range(1, src.max_row + 1):
        for col in range(1, src.max_column + 1):
            s, d = src.cell(row, col), ws.cell(row, col)
            d.value = s.value
            if s.has_style:
                d.font, d.fill = copy(s.font), copy(s.fill)
                d.border, d.alignment = copy(s.border), copy(s.alignment)
        ws.row_dimensions[row].height = src.row_dimensions[row].height
    for key, dim in src.column_dimensions.items():
        ws.column_dimensions[key].width = dim.width
    for rng in src.merged_cells.ranges:
        ws.merge_cells(str(rng))


def add_mapeo(wb, traza: dict[str, tuple[str, str]], original: dict[str, str]) -> None:
    ws = wb.create_sheet("MAPEO")
    ws.append(["MAPEO DE TRAZABILIDAD"])
    ws.append([])
    ws.append(
        [
            "El backlog se depuró el 2026-09-12: salieron 6 historias técnicas y se "
            "renumeró cerrando huecos. Esta hoja relaciona cada caso con su "
            "identificador anterior y el nuevo."
        ]
    )
    ws.append([])
    ws.append(["Caso", "Criterio anterior", "Criterio nuevo", "¿Cambió?"])
    for cp in sorted(traza):
        old, new = original[cp], traza[cp][1]
        ws.append([cp, old, new, "Sí" if old != new else "No"])
    ws["A1"].font = Font(sz=12, b=True)
    for cell in ws[5]:
        cell.font = Font(sz=10, b=True)
    ws["A3"].alignment = Alignment(wrap_text=True, vertical="top")
    for col, width in (("A", 12), ("B", 20), ("C", 20), ("D", 12)):
        ws.column_dimensions[col].width = width


# ── Verificación ──────────────────────────────────────────────────────────


def verify(dst: Path) -> list[str]:
    problems: list[str] = []
    wb = load_workbook(dst)

    cases = [n for n in wb.sheetnames if re.fullmatch(r"CP\d{3}", n)]
    if len(cases) != 87:
        problems.append(f"Se esperaban 87 hojas de caso; hay {len(cases)}")
    expected = [f"CP{i:03d}" for i in range(1, 88)]
    if cases != expected:
        problems.append("Las hojas de caso no son CP001-CP087 correlativas")

    for name in ("LISTA CP", "RESUMEN", "GLOSARIO", "MAPEO"):
        if name not in wb.sheetnames:
            problems.append(f"Falta la hoja '{name}'")

    hus: set[str] = set()
    crits: set[str] = set()
    for name in cases:
        ws = wb[name]
        text = str(ws.cell(ROW_HU, 1).value or "")
        m = re.search(r"HU relacionada: (HU\d+)\. Escenario (\d+)\. Criterio (\S+?)\.", text)
        if not m:
            problems.append(f"{name}: trazabilidad ilegible ({text!r})")
            continue
        hu, crit = m.group(1), m.group(3)
        if int(hu[2:]) > 40:
            problems.append(f"{name}: apunta a {hu}, fuera del backlog depurado")
        if crit != f"{hu}-{m.group(2)}":
            problems.append(f"{name}: criterio {crit} incoherente con {hu}")
        hus.add(hu)
        crits.add(crit)
        if ws.cell(ROW_STEP_HEADER, COL_RESULTADO).value != "Resultado obtenido":
            problems.append(f"{name}: falta la columna de resultado")
        if ws.cell(EXEC_FIRST_ROW, 1).value != "REGISTRO DE EJECUCIÓN":
            problems.append(f"{name}: falta el bloque de ejecución")
        if not ws.cell(EXEC_FIRST_ROW + 1, 3).value:
            problems.append(f"{name}: sin estado inicial")

    if len(hus) != 40:
        problems.append(f"Cobertura: {len(hus)} historias, se esperaban 40")
    if len(crits) != 80:
        problems.append(f"Cobertura: {len(crits)} criterios, se esperaban 80")

    idx = wb[SHEET_INDEX]
    listed = [
        str(idx.cell(r, IDX_COL_CP).value or "").strip()
        for r in range(IDX_FIRST_ROW, IDX_LAST_ROW + 1)
    ]
    if listed != expected:
        problems.append("El índice no lista los 87 casos en orden")
    for r in range(IDX_FIRST_ROW, IDX_LAST_ROW + 1):
        if not idx.cell(r, IDX_COL_ESTADO).value:
            problems.append(f"Índice: fila {r} sin estado inicial")
            break

    return problems


# ── Entrada ───────────────────────────────────────────────────────────────


def main() -> int:
    if not SRC.exists():
        print(f"No existe el archivo de entrada: {SRC}", file=sys.stderr)
        return 1

    shutil.copy(SRC, DST)
    wb = load_workbook(DST)

    cases = [n for n in wb.sheetnames if re.fullmatch(r"CP\d{3}", n)]
    print(f"Procesando {len(cases)} casos…")

    original: dict[str, str] = {}
    traza: dict[str, tuple[str, str]] = {}
    for name in cases:
        ws = wb[name]
        raw = str(ws.cell(ROW_HU, 1).value or "")
        m = re.search(r"(HU\d+)\.\s*Escenario\s*(\d+)", raw)
        original[name] = f"{m.group(1)}-{m.group(2)}" if m else "?"
        traza[name] = process_case(ws, name)

    update_index(wb[SHEET_INDEX], traza)
    add_resumen(wb, traza)
    add_glosario(wb, SRC_GLOSARIO)
    add_mapeo(wb, traza, original)

    # Las hojas de referencia van delante de los 87 casos, no al final.
    front = [SHEET_INDEX, "RESUMEN", "GLOSARIO", "MAPEO"]
    wb._sheets = [wb[n] for n in front if n in wb.sheetnames] + [
        wb[n] for n in wb.sheetnames if n not in front
    ]
    wb.save(DST)

    problems = verify(DST)
    if problems:
        DST.unlink(missing_ok=True)
        print("\nVerificación fallida, no se escribió el archivo:", file=sys.stderr)
        for p in problems[:20]:
            print(f"  - {p}", file=sys.stderr)
        return 1

    changed = sum(1 for cp in traza if original[cp] != traza[cp][1])
    print(f"\nOK: {DST.relative_to(ROOT)}")
    print(f"  87 casos · 40 historias · 80 criterios")
    print(f"  {changed} casos cambiaron de criterio, {87 - changed} lo conservan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
