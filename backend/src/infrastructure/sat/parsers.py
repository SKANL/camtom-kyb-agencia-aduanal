import pandas as pd
from domain.rfc import normalize_rfc

# Encabezados a confirmar contra el archivo real descargado (paso de
# verificación de esta misma tarea) — el SAT no publica diccionario de
# datos estable. Único lugar del código que conoce el formato crudo.
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
    fracciones = {f.strip() for f in fraccion_raw.replace(",", ";").split(";") if f.strip()}
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
