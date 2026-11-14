#!/usr/bin/env python3
"""Limpieza del backlog de historias de usuario (spec 2026-09-12).

Toma `docs/HU_y_Criterios_de_Aceptacion_Chatbot_RAG_v1.xlsx` y produce la versión
v2 aplicando tres cambios:

1. Elimina 6 historias que no son historias de usuario (rol "Desarrollador" o
   infraestructura disfrazada de necesidad del administrador).
2. Reescribe las 9 historias de rol "Sistema" hacia el usuario que recibe el valor
   (5 al estudiante, 4 al administrador). Sus criterios no cambian.
3. Renumera cerrando huecos: 46 -> 40 historias, HU01-HU40 corrido.

Por qué se edita el archivo en sitio y no se genera desde cero: la plantilla de la
universidad trae celdas combinadas, encabezados de dos niveles y estilos que el
entregable debe conservar.

Detalle de implementación que condiciona todo el script: la hoja de historias tiene
una estructura regular de 3 filas por historia (escenario 1, escenario 2, fila
separadora) con las columnas de enunciado combinadas verticalmente sobre las dos
filas de escenario. openpyxl no reajusta los rangos combinados al desplazar filas,
así que NO se borran filas intermedias: se reescriben los valores en sitio
conservando el bloque de 3 filas y al final se eliminan solo las filas sobrantes de
la cola, donde no hay nada debajo que desplazar.

Las columnas G (REDACCION) y J (ID de criterio) son fórmulas que referencian la
propia fila del bloque, así que se recalculan solas al cambiar A/B/D/F.

Uso:
    uv run --no-project --with openpyxl python tools/fix_backlog_xlsx.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "HU_y_Criterios_de_Aceptacion_Chatbot_RAG_v1.xlsx"
DST = ROOT / "docs" / "HU_y_Criterios_de_Aceptacion_Chatbot_RAG_v2.xlsx"

SHEET_HU = "HIstoria de Usuario"  # la errata es de la plantilla original
SHEET_EP = "EPICAS"
UNTOUCHED = ("Instructivo", "Ejemplo")

# Layout de la hoja de historias.
HU_FIRST_ROW = 3
ROWS_PER_HU = 3  # escenario 1, escenario 2, separadora
COL_ID, COL_ROL, COL_CARACT, COL_RAZON = 1, 2, 4, 6

# Layout de la hoja de épicas (B=épica, C=objetivo, D=id de historia).
EP_FIRST_ROW = 3
EP_COL_EPICA, EP_COL_OBJETIVO, EP_COL_HU = 2, 3, 4

# ── Cambios declarados en el spec ─────────────────────────────────────────

# Historias que salen del backlog, con el motivo que va en la hoja MAPEO.
REMOVED: dict[str, str] = {
    "HU18": "Tarea de desarrollo: levantar el entorno no es una necesidad de un usuario del producto.",
    "HU19": "Herramienta interna del equipo de desarrollo, no funcionalidad del producto.",
    "HU24": "Configuración técnica. El valor para el usuario está en la alerta al administrador (ahora HU20).",
    "HU33": "Tarea de despliegue inicial de la base de conocimiento.",
    "HU45": "Decisión de arquitectura (Amazon S3), no una necesidad del administrador.",
    "HU47": "Práctica de ingeniería (CI/CD), fuera del alcance funcional.",
}

# Historias de rol "Sistema" reescritas: id anterior -> (rol, característica, razón).
REWRITES: dict[str, tuple[str, str, str]] = {
    "HU04": (
        "Estudiante universitario",
        "que mi consulta se atienda aunque varios estudiantes escriban al mismo "
        "tiempo y aunque WhatsApp entregue mi mensaje más de una vez",
        "recibir una sola respuesta y no quedarme esperando porque el sistema esté "
        "atendiendo a otro.",
    ),
    "HU06": (
        "Administrador del sistema",
        "consultar la intención detectada y el nivel de certeza de cada mensaje del "
        "estudiante",
        "monitorear la calidad de la clasificación e identificar los temas donde el "
        "chatbot se equivoca.",
    ),
    "HU11": (
        "Estudiante universitario",
        "que el chatbot busque en los documentos oficiales tomando en cuenta lo que "
        "ya venimos conversando",
        "que su respuesta se refiera a mi consulta real y no a otro tema parecido.",
    ),
    "HU13": (
        "Administrador del sistema",
        "que los documentos que cargo se procesen automáticamente, incluidos los "
        "escaneados o en imagen",
        "no transcribir nada a mano y que su contenido quede disponible para el "
        "chatbot.",
    ),
    "HU17": (
        "Estudiante universitario",
        "que el chatbot recupere lo que hablamos aunque haya pasado más de un día "
        "desde mi último mensaje",
        "retomar mi consulta sin volver a explicar todo desde cero.",
    ),
    "HU21": (
        "Administrador del sistema",
        "que las conversaciones donde el chatbot no entendió la consulta con "
        "suficiente certeza queden registradas como escaladas",
        "identificarlas y priorizarlas sin revisar una por una.",
    ),
    "HU26": (
        "Administrador del sistema",
        "que cada conversación y sus mensajes queden guardados con la intención "
        "detectada y su certeza",
        "revisar el historial completo desde el sistema web y que los indicadores de "
        "uso sean calculables.",
    ),
    "HU39": (
        "Estudiante universitario",
        "que el chatbot me reconozca por mi número de WhatsApp sin que yo tenga que "
        "escribir mi carrera, ciclo ni código",
        "recibir respuestas que consideren mi situación académica real desde el "
        "primer mensaje.",
    ),
    "HU43": (
        "Estudiante universitario",
        "que el chatbot entienda cuando le pregunto por mis pagos, aunque lo diga de "
        "distintas formas",
        "recibir el estado de mis cuotas y no una explicación general de medios de "
        "pago.",
    ),
}

# Objetivos de épica que quedaron desactualizados al salir historias.
EPIC_OBJETIVOS: dict[str, str] = {
    "EP03": (
        "Búsqueda semántica en documentos oficiales y generación de respuestas con "
        "IA. La base de conocimiento se mantiene actualizada cada ciclo mediante la "
        "carga manual de documentos por parte del administrador desde el sistema "
        "web. Incluye procesamiento de documentos con texto plano y con contenido en "
        "imagen mediante OCR."
    ),
    "EP04": (
        "Continuidad de la conversación. El chatbot conserva el contexto de cada "
        "conversación durante 24 horas y lo recupera del registro histórico cuando ha "
        "expirado, para que el estudiante retome su consulta sin repetir lo que ya "
        "contó."
    ),
}


# ── Lectura ───────────────────────────────────────────────────────────────


def read_historias(ws: Worksheet) -> list[dict[str, object]]:
    """Bloques de la hoja de historias, en orden, tal como están en el original."""
    historias: list[dict[str, object]] = []
    row = HU_FIRST_ROW
    while row <= ws.max_row:
        hu_id = ws.cell(row, COL_ID).value
        if not hu_id:
            break
        historias.append(
            {
                "id": str(hu_id).strip(),
                "rol": ws.cell(row, COL_ROL).value,
                "caract": ws.cell(row, COL_CARACT).value,
                "razon": ws.cell(row, COL_RAZON).value,
                "row": row,
            }
        )
        row += ROWS_PER_HU
    return historias


def read_epicas(ws: Worksheet) -> list[tuple[str, str, str]]:
    """(épica, objetivo, id de historia) por fila, propagando las celdas combinadas."""
    filas: list[tuple[str, str, str]] = []
    epica = objetivo = ""
    for row in range(EP_FIRST_ROW, ws.max_row + 1):
        hu_id = ws.cell(row, EP_COL_HU).value
        if not hu_id:
            continue
        epica = str(ws.cell(row, EP_COL_EPICA).value or epica).strip()
        objetivo = str(ws.cell(row, EP_COL_OBJETIVO).value or objetivo).strip()
        filas.append((epica, objetivo, str(hu_id).strip()))
    return filas


# ── Transformación ────────────────────────────────────────────────────────


def build_renumber_map(historias: list[dict[str, object]]) -> dict[str, str]:
    """id anterior -> id nuevo, cerrando huecos sobre las historias que quedan."""
    kept = [h for h in historias if h["id"] not in REMOVED]
    return {str(h["id"]): f"HU{i:02d}" for i, h in enumerate(kept, start=1)}


def write_historias(
    ws: Worksheet,
    historias: list[dict[str, object]],
    renumber: dict[str, str],
) -> None:
    """Reescribe los bloques en sitio y elimina la cola sobrante.

    El contenido de los criterios (columnas H-M) no se toca: al mover un bloque de
    una posición a otra habría que arrastrarlo, así que en vez de mover bloques
    reescribimos solo las 4 columnas de enunciado y dejamos cada criterio donde
    está. Eso obliga a copiar también los criterios cuando el bloque cambia de
    posición, cosa que hacemos abajo celda a celda.
    """
    kept = [h for h in historias if h["id"] not in REMOVED]

    # Snapshot de las celdas de criterio (H-M) de cada bloque conservado, porque al
    # compactar los bloques hacia arriba se sobrescriben posiciones.
    snapshots = []
    for h in kept:
        src = int(h["row"])  # type: ignore[call-overload]
        snapshots.append(
            [
                [ws.cell(src + offset, col).value for col in range(8, 14)]
                for offset in (0, 1)
            ]
        )

    for i, (h, criterios) in enumerate(zip(kept, snapshots, strict=True)):
        dst = HU_FIRST_ROW + i * ROWS_PER_HU
        old_id = str(h["id"])
        rol, caract, razon = REWRITES.get(
            old_id, (h["rol"], h["caract"], h["razon"])
        )

        ws.cell(dst, COL_ID).value = renumber[old_id]
        ws.cell(dst, COL_ROL).value = rol
        ws.cell(dst, COL_CARACT).value = caract
        ws.cell(dst, COL_RAZON).value = razon

        for offset in (0, 1):
            for j, col in enumerate(range(8, 14)):
                cell = ws.cell(dst + offset, col)
                # J es la fórmula del id de criterio y referencia su propia fila:
                # se deja intacta para que siga apuntando al bloque correcto.
                if col == 10:
                    continue
                cell.value = criterios[offset][j]

    last_row = HU_FIRST_ROW + len(kept) * ROWS_PER_HU - 1
    drop_from = last_row + 1
    if drop_from <= ws.max_row:
        for rng in list(ws.merged_cells.ranges):
            if rng.min_row >= drop_from:
                ws.unmerge_cells(str(rng))
        ws.delete_rows(drop_from, ws.max_row - drop_from + 1)


def write_epicas(
    ws: Worksheet,
    filas: list[tuple[str, str, str]],
    renumber: dict[str, str],
) -> None:
    """Reescribe la hoja de épicas y rehace las combinaciones por bloque."""
    kept = [
        (epica, EPIC_OBJETIVOS.get(epica, objetivo), renumber[hu])
        for epica, objetivo, hu in filas
        if hu not in REMOVED
    ]

    for rng in list(ws.merged_cells.ranges):
        if rng.min_row >= EP_FIRST_ROW:
            ws.unmerge_cells(str(rng))

    for i, (epica, objetivo, hu) in enumerate(kept):
        row = EP_FIRST_ROW + i
        ws.cell(row, EP_COL_EPICA).value = epica
        ws.cell(row, EP_COL_OBJETIVO).value = objetivo
        ws.cell(row, EP_COL_HU).value = hu

    drop_from = EP_FIRST_ROW + len(kept)
    if drop_from <= ws.max_row:
        ws.delete_rows(drop_from, ws.max_row - drop_from + 1)

    # Re-combinar épica y objetivo sobre las filas de cada bloque.
    start = 0
    while start < len(kept):
        end = start
        while end + 1 < len(kept) and kept[end + 1][0] == kept[start][0]:
            end += 1
        if end > start:
            top, bottom = EP_FIRST_ROW + start, EP_FIRST_ROW + end
            for col in (EP_COL_EPICA, EP_COL_OBJETIVO):
                letter = get_column_letter(col)
                ws.merge_cells(f"{letter}{top}:{letter}{bottom}")
        start = end + 1


def write_mapeo(wb, historias: list[dict[str, object]], renumber: dict[str, str]) -> None:
    """Hoja nueva con la equivalencia de identificadores y las bajas."""
    if "MAPEO" in wb.sheetnames:
        del wb["MAPEO"]
    ws = wb.create_sheet("MAPEO")

    titles = {str(h["id"]): str(h["caract"] or "") for h in historias}

    ws.append(["MAPEO DE IDENTIFICADORES"])
    ws.append([])
    ws.append(["Historias conservadas"])
    ws.append(["ID anterior", "ID nuevo", "Necesito"])
    for old, new in renumber.items():
        ws.append([old, new, titles.get(old, "")])
    ws.append([])
    ws.append(["Historias eliminadas"])
    ws.append(["ID anterior", "Motivo de la baja", "Necesito"])
    for old, motivo in REMOVED.items():
        ws.append([old, motivo, titles.get(old, "")])

    for col, width in (("A", 14), ("B", 60), ("C", 80)):
        ws.column_dimensions[col].width = width


# ── Verificación ──────────────────────────────────────────────────────────


def verify(dst: Path, src: Path) -> list[str]:
    """Comprueba el resultado. Devuelve la lista de problemas encontrados."""
    problems: list[str] = []
    new = load_workbook(dst)
    old = load_workbook(src)

    # Los identificadores se reciclan al renumerar (el antiguo HU20 pasa a ser
    # HU18), así que la baja se comprueba por contenido, no por ID.
    dropped_texts = {
        str(h["caract"] or "").strip()
        for h in read_historias(old[SHEET_HU])
        if h["id"] in REMOVED
    }

    ws = new[SHEET_HU]
    historias = read_historias(ws)

    ids = [h["id"] for h in historias]
    expected = [f"HU{i:02d}" for i in range(1, 41)]
    if ids != expected:
        problems.append(f"IDs esperados HU01-HU40 correlativos; se obtuvo {ids}")

    for h in historias:
        rol = str(h["rol"] or "").strip()
        if rol in ("Sistema", "Desarrollador"):
            problems.append(f"{h['id']} conserva el rol '{rol}'")
        if not str(h["caract"] or "").strip():
            problems.append(f"{h['id']} sin característica")
        if not str(h["razon"] or "").strip():
            problems.append(f"{h['id']} sin razón")

    criterios = 0
    for h in historias:
        row = int(h["row"])  # type: ignore[call-overload]
        for offset in (0, 1):
            if ws.cell(row + offset, 9).value:
                criterios += 1
    if criterios != 80:
        problems.append(f"Se esperaban 80 criterios; hay {criterios}")

    still_there = [
        h["id"]
        for h in historias
        if str(h["caract"] or "").strip() in dropped_texts
    ]
    if still_there:
        problems.append(
            f"Contenido de historias eliminadas todavía presente en: {still_there}"
        )

    ep = read_epicas(new[SHEET_EP])
    if len(ep) != 40:
        problems.append(f"EPICAS lista {len(ep)} historias; se esperaban 40")
    ep_ids = {hu for _, _, hu in ep}
    if ep_ids != set(expected):
        problems.append("Los IDs de EPICAS no coinciden con la hoja de historias")
    if len({e for e, _, _ in ep}) != 8:
        problems.append("EPICAS ya no tiene 8 épicas")

    for name in UNTOUCHED:
        a, b = old[name], new[name]
        if a.max_row != b.max_row or a.max_column != b.max_column:
            problems.append(f"La hoja '{name}' cambió de dimensiones")
            continue
        for row in range(1, a.max_row + 1):
            for col in range(1, a.max_column + 1):
                if a.cell(row, col).value != b.cell(row, col).value:
                    problems.append(
                        f"La hoja '{name}' cambió en "
                        f"{get_column_letter(col)}{row}"
                    )
                    break

    return problems


# ── Entrada ───────────────────────────────────────────────────────────────


def main() -> int:
    if not SRC.exists():
        print(f"No existe el archivo de entrada: {SRC}", file=sys.stderr)
        return 1

    wb = load_workbook(SRC)
    ws_hu, ws_ep = wb[SHEET_HU], wb[SHEET_EP]

    historias = read_historias(ws_hu)
    epicas = read_epicas(ws_ep)
    renumber = build_renumber_map(historias)

    print(f"Leídas {len(historias)} historias, {len(epicas)} filas de épicas.")
    print(f"Se eliminan {len(REMOVED)}, se reescriben {len(REWRITES)}.")

    write_historias(ws_hu, historias, renumber)
    write_epicas(ws_ep, epicas, renumber)
    write_mapeo(wb, historias, renumber)
    wb.save(DST)

    problems = verify(DST, SRC)
    if problems:
        DST.unlink(missing_ok=True)
        print("\nVerificación fallida, no se escribió el archivo:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"\nOK: {DST.relative_to(ROOT)}")
    print("  40 historias HU01-HU40, 80 criterios, 8 épicas.")
    print("  Instructivo y Ejemplo idénticos al original.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
