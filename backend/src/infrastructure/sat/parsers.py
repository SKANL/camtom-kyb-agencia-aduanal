import pandas as pd
from domain.rfc import normalize_rfc

# Encabezados a confirmar contra el archivo real descargado (paso de
# verificación de esta misma tarea) — el SAT no publica diccionario de
# datos estable. Único lugar del código que conoce el formato crudo.
ART_69_COLUMNS = {"rfc": "RFC", "situacion": "Situación del contribuyente", "fraccion": "Fracción"}


def parse_art_69(xlsx_path: str) -> list[dict]:
    df = pd.read_excel(xlsx_path)
    rows = []
    for _, row in df.iterrows():
        rfc = normalize_rfc(str(row[ART_69_COLUMNS["rfc"]]))
        if not rfc:
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
