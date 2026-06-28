import csv
import os

import pandas as pd
from src.domain.rfc import normalize_rfc

# ── XLSX parsers (original, para formulario web del SAT) ──────────────

ART_69_COLUMNS = {"rfc": "RFC", "situacion": "Situación del contribuyente", "fraccion": "Fracción"}

ART_69B_COLUMNS = {"rfc": "RFC", "razon_social": "Nombre del Contribuyente", "situacion": "Situación del Contribuyente"}

_ART_69B_SUBSTATE_MAP = {
    "presunto": "presunto", "presuntos": "presunto",
    "desvirtuado": "desvirtuado",
    "definitivo": "definitivo", "definitivos": "definitivo",
    "sentencia favorable": "sentencia_favorable",
}


def parse_art_69(xlsx_path: str) -> list[dict]:
    df = pd.read_excel(xlsx_path)
    rows = []
    for _, row in df.iterrows():
        rfc = normalize_rfc(str(row[ART_69_COLUMNS["rfc"]]))
        if not rfc or rfc == "NAN":
            continue
        rows.append({
            "rfc": rfc,
            "situacion": str(row[ART_69_COLUMNS["situacion"]]),
            "fraccion": str(row.get(ART_69_COLUMNS["fraccion"], "")).strip(),
        })
    return rows


def es_unicamente_fraccion_vi(fraccion_raw: str) -> bool:
    fracciones = {f.strip().upper() for f in fraccion_raw.replace(",", ";").split(";") if f.strip()}
    return fracciones == {"VI"}


def parse_art_69b(xlsx_path: str) -> list[dict]:
    df = pd.read_excel(xlsx_path)
    rows = []
    for _, row in df.iterrows():
        rfc = normalize_rfc(str(row[ART_69B_COLUMNS["rfc"]]))
        situacion_raw = str(row[ART_69B_COLUMNS["situacion"]]).strip().lower()
        if rfc in ("", "NAN") or situacion_raw in ("", "nan"):
            continue
        if situacion_raw not in _ART_69B_SUBSTATE_MAP:
            raise ValueError(
                f"situacion no mapeada en Art. 69-B: {situacion_raw!r} (RFC {rfc}). "
                "Agregar la variante a _ART_69B_SUBSTATE_MAP antes de ingerir este archivo: "
                "un sub-estado sin mapear se perderia silenciosamente y un bloqueo critico "
                "(sat_69b_definitivo) podria no aplicarse."
            )
        rows.append({
            "rfc": rfc,
            "razon_social": str(row[ART_69B_COLUMNS["razon_social"]]),
            "art69b_substate": _ART_69B_SUBSTATE_MAP[situacion_raw],
            "situacion": situacion_raw,
        })
    return rows


# ── CSV parsers (para archivos Datos Abiertos del SAT) ────────────────
# Estos CSVs vienen del portal https://www.sat.gob.mx/minisitio/DatosAbiertos/
# y tienen una estructura común: filas disclaimer, fila de encabezados, datos.

_ART_69_69B_HEADER_KEYWORDS = ("RFC",)
"""Palabras clave que identifican la fila de encabezados en CSVs SAT."""


def _detect_csv_encoding(path: str) -> str:
    """Determina la codificación de un CSV del SAT.

    Todos los archivos del portal Datos Abiertos SAT vienen en
    ISO-8859-1 (latin-1). La única excepción posible es el BOM de
    UTF-8 si fueron re-exportados por herramientas de escritorio.

    NOTA: No intentamos detectar UTF-8 sin BOM porque archivos como
    Firmes.csv tienen encabezados en ASCII puro (primeros KB válidos
    como UTF-8) pero el cuerpo contiene bytes 0xD1 (Ñ) que son
    latin-1 inválidos como UTF-8 — y no vale la pena escanear
    200MB+ para decidir.
    """
    with open(path, "rb") as f:
        raw = f.read(8)
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    return "latin-1"


def _find_header_row(path: str, encoding: str) -> int:
    """Encuentra el índice (0-based) de la fila de encabezados.

    Los CSVs del SAT tienen 1-3 filas de disclaimer/título antes de la
    fila con los nombres de columna. Busca una fila que contenga 'RFC'
    y un indicador de nombre/contribuyente.
    """
    with open(path, "r", encoding=encoding) as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            line_text = " ".join(row).upper()
            if "RFC" in line_text and "NOMBRE" in line_text:
                return i
        return 0


def _resolve_column_by_pattern(row: dict, patterns: tuple[str, ...]) -> str:
    """Busca un valor por patrón en las claves del dict (case-insensitive)."""
    for key in row:
        key_upper = key.upper().strip()
        for pat in patterns:
            if pat in key_upper:
                val = (row[key] or "").strip()
                return val
    return ""


def _parse_csv_art_69(path: str, encoding: str, header_row: int, filename: str) -> list[dict]:
    """Parsea un sub-archivo CSV de contribuyentes incumplidos (Art. 69 CFF).

    Columnas típicas: RFC, RAZÓN SOCIAL, TIPO PERSONA, SUPUESTO, ...
    El SUPUESTO contiene la categoría (Cancelados, Firmes, Exigibles, etc.).
    """
    rows = []
    with open(path, "r", encoding=encoding) as f:
        for _ in range(header_row):
            next(f)
        reader = csv.DictReader(f)
        for csv_row in reader:
            rfc_raw = (csv_row.get("RFC") or "").strip()
            if not rfc_raw:
                continue
            rfc = normalize_rfc(rfc_raw)
            if not rfc or rfc == "NAN":
                continue
            razon = _resolve_column_by_pattern(csv_row, ("RAZÓN SOCIAL", "RAZON SOCIAL", "RAZÓN"))
            supuesto = _resolve_column_by_pattern(csv_row, ("SUPUESTO",))
            rows.append({
                "rfc": rfc,
                "razon_social": razon,
                "situacion": supuesto,
            })
    return rows


def _parse_csv_art_69b(path: str, encoding: str, header_row: int, is_subfile: bool) -> list[dict]:
    """Parsea un archivo CSV de EFOS (Art. 69-B CFF).

    Columnas: No., RFC, Nombre del Contribuyente, Situación del contribuyente, ...
    - is_subfile=True: archivos como Definitivos.csv, Presuntos.csv, etc.
      donde la situación es homogénea (inferida del nombre del archivo).
    - is_subfile=False: Listado_completo_69-B.csv con situación variable por fila.
    """
    rows = []
    with open(path, "r", encoding=encoding) as f:
        for _ in range(header_row):
            next(f)
        reader = csv.DictReader(f)
        for csv_row in reader:
            rfc_raw = (csv_row.get("RFC") or "").strip()
            if not rfc_raw:
                continue
            rfc = normalize_rfc(rfc_raw)
            if not rfc or rfc == "NAN":
                continue
            nombre = _resolve_column_by_pattern(csv_row, ("NOMBRE DEL", "NOMBRE DEL CONTRIBUYENTE", "NOMBRE"))
            situacion_raw = _resolve_column_by_pattern(csv_row, ("SITUACIÓN DEL", "SITUACION DEL")).lower()
            if situacion_raw:
                if situacion_raw not in _ART_69B_SUBSTATE_MAP:
                    raise ValueError(
                        f"situacion no mapeada en Art. 69-B: {situacion_raw!r} (RFC {rfc}). "
                        f"Agregar la variante a _ART_69B_SUBSTATE_MAP."
                    )
            rows.append({
                "rfc": rfc,
                "razon_social": nombre,
                "art69b_substate": _ART_69B_SUBSTATE_MAP.get(situacion_raw) if situacion_raw else None,
                "situacion": situacion_raw,
            })
    return rows


def _parse_csv_art_69b_bis(path: str, encoding: str, header_row: int) -> list[dict]:
    """Parsea un archivo CSV de transmisión indebida de pérdidas (Art. 69-B Bis).

    Misma estructura que 69-B: No., RFC, Nombre, Situación, ...
    """
    return _parse_csv_art_69b(path, encoding, header_row, is_subfile=False)


def parse_sat_csv(path: str) -> list[dict]:
    """Parsea cualquier archivo CSV del SAT (Datos Abiertos) basado en su
    estructura y path dentro de la jerarquía ``backend/data/sat/``.

    La función detecta automáticamente:
    - El tipo de lista (art_69 / art_69b / art_69b_bis) según la carpeta
    - La codificación del archivo (latin-1, utf-8-sig)
    - La fila de encabezados (skip disclaimer rows)

    Returns:
        list[dict]: Registros listos para insertar en ``sat_lista_registros``.
            Cada dict incluye ``list_type`` y las columnas específicas del tipo.
    """
    filename = os.path.basename(path)
    rel = os.path.normpath(path)
    rel_lower = rel.lower()

    # Determinar list_type por la ruta
    if "articulo-69b-bis" in rel_lower or "documents_aggc" in rel_lower:
        list_type = "art_69b_bis"
    elif "articulo-69b" in rel_lower or "documents_agaff" in rel_lower:
        list_type = "art_69b"
    elif "articulo-69" in rel_lower or "documents_agr" in rel_lower:
        list_type = "art_69"
    else:
        raise ValueError(f"No se pudo determinar list_type para: {path}")

    enc = _detect_csv_encoding(path)
    header_row = _find_header_row(path, enc)

    if list_type == "art_69":
        raw_rows = _parse_csv_art_69(path, enc, header_row, filename)
    elif list_type == "art_69b":
        is_subfile = filename.lower() not in ("listado_completo_69-b.csv", "listado_completo_69-b.csv")
        raw_rows = _parse_csv_art_69b(path, enc, header_row, is_subfile)
    else:
        raw_rows = _parse_csv_art_69b_bis(path, enc, header_row)

    # Agregar list_type y source_url (inferida de la ruta)
    for r in raw_rows:
        r["list_type"] = list_type
    return raw_rows
