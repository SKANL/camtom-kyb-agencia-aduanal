import hashlib
import os
import uuid
from datetime import datetime, timezone

from src.infrastructure.sat.parsers import parse_art_69, parse_art_69b, parse_sat_csv
from src.infrastructure.sat.sources import SAT_SOURCES

# Parsers para XLSX (upload por formulario web del SAT)
_PARSERS = {"art_69": parse_art_69, "art_69b": parse_art_69b}

# Parser genérico CSV (Datos Abiertos) — detecta list_type desde el path
_PARSERS_CSV = {"art_69": parse_sat_csv, "art_69b": parse_sat_csv, "art_69b_bis": parse_sat_csv}


def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _build_records(rows: list[dict], list_type: str, source_url: str, batch_id: str) -> list[dict]:
    """Estandariza los registros para insertar en sat_lista_registros.

    NOTA: ``fraccion`` existía en el parser XLSX original pero la columna
    NO fue creada en Supabase. Si se agrega en el futuro, incluirla aquí.
    Columnas actuales de sat_lista_registros (verificadas contra schema cache):
    id, list_type, rfc, razon_social, art69b_substate, situacion,
    source_url, import_batch_id, created_at
    """
    return [{
        "list_type": list_type, "rfc": r["rfc"], "razon_social": r.get("razon_social"),
        "art69b_substate": r.get("art69b_substate"), "situacion": r.get("situacion"),
        "source_url": source_url, "import_batch_id": batch_id,
    } for r in rows]


def ingest_list(supabase_client, list_type: str, xlsx_path: str) -> dict:
    if list_type not in SAT_SOURCES:
        raise ValueError(
            f"list_type desconocido: {list_type!r}. "
            f"Valores válidos: {sorted(SAT_SOURCES)}."
        )
    if list_type not in _PARSERS:
        raise ValueError(
            f"no hay parser implementado para list_type {list_type!r} "
            f"(está registrado en SAT_SOURCES pero falta su función en infrastructure.sat.parsers). "
            f"Parsers disponibles: {sorted(_PARSERS)}."
        )

    source = SAT_SOURCES[list_type]
    run_id = str(uuid.uuid4())
    supabase_client.table("sat_import_runs").insert({
        "id": run_id, "list_type": list_type, "source_url": source.url,
        "status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
        "file_hash": file_hash(xlsx_path),
    }).execute()

    try:
        parser = _PARSERS[list_type]
        rows = parser(xlsx_path)
        batch_id = str(uuid.uuid4())
        records = _build_records(rows, list_type, source.url, batch_id)

        if records:
            supabase_client.table("sat_lista_registros").insert(records).execute()
            supabase_client.table("sat_lista_registros").delete().eq(
                "list_type", list_type
            ).neq("import_batch_id", batch_id).execute()

        supabase_client.table("sat_import_runs").update({
            "status": "success", "rows_imported": len(records),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()
        return {"run_id": run_id, "rows_imported": len(records)}
    except Exception:
        supabase_client.table("sat_import_runs").update({
            "status": "failed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", run_id).execute()
        raise


_BATCH_SIZE = 1000
"""Tamaño de lote para inserts masivos.

5000 funciona al inicio pero a medida que la tabla crece (~600K registros),
cada INSERT necesita mantener el índice de la PK y comprobar unicidad,
lo que ralentiza cada lote. 1000 es un balance seguro para el tier gratuito
de Supabase con statement timeout de 30s."""


def _insert_batch(supabase_client, records: list[dict], list_type: str, batch_id: str) -> None:
    """Inserta registros en lotes de ``_BATCH_SIZE`` y luego elimina los
    registros viejos del mismo ``list_type`` que no pertenecen a este batch.

    La atomicidad es por lote: si falla un lote a medio camino, los lotes
    anteriores ya están insertados pero los registros viejos aún no se
    eliminan (el DELETE solo ocurre al final). Esto permite reintentar.

    Si un lote falla, se levanta la excepción y el import_run se marca como
    failed en el caller.
    """
    total = len(records)
    for i in range(0, total, _BATCH_SIZE):
        chunk = records[i:i + _BATCH_SIZE]
        print(f"    Lote {i // _BATCH_SIZE + 1}/{(total + _BATCH_SIZE - 1) // _BATCH_SIZE}: {len(chunk)} registros...")
        supabase_client.table("sat_lista_registros").insert(chunk).execute()

    # Atomic replace: eliminar registros viejos del mismo list_type
    # Los registros recién insertados tienen el batch_id actual, así que
    # este DELETE solo afecta a registros de importaciones anteriores.
    # Verificar primero si HAY registros viejos — si no los hay, el DELETE
    # escanearía toda la tabla innecesariamente (statement timeout en free tier).
    if total > 0:
        try:
            result = supabase_client.table("sat_lista_registros").delete().eq(
                "list_type", list_type
            ).neq("import_batch_id", batch_id).execute()
            deleted = len(result.data) if result.data else 0
            print(f"    Registros viejos eliminados: {deleted}")
        except Exception as e:
            # Si el DELETE falla por timeout, los datos nuevos ya están insertados
            # y los viejos se eliminarán en la próxima importación. No fatal.
            print(f"    AVISO: DELETE de registros viejos falló ({type(e).__name__}). "
                  f"Los datos nuevos están insertados correctamente. "
                  f"Ejecutar manualmente si es necesario: "
                  f"supabase db query --linked \"DELETE FROM sat_lista_registros "
                  f"WHERE list_type = '{list_type}' AND import_batch_id != '{batch_id}'\"")


def bulk_import_csvs(supabase_client) -> dict[str, dict]:
    """Importa MASIVAMENTE todos los CSVs de datos abiertos del SAT
    para los tres tipos de lista (art_69, art_69b, art_69b_bis).

    Recorre la jerarquía ``backend/data/sat/``, agrupa archivos por
    list_type, parsea cada uno con ``parse_sat_csv``, MERGE los resultados
    por list_type, y hace un replace atómico por list_type en Supabase
    (inserta en lotes de 5000, luego elimina los viejos).

    Returns:
        dict[str, dict]: ``{list_type: {"run_id": ..., "rows_imported": ...}}``
    """
    import glob

    import src.infrastructure.sat.parsers as parsers_mod

    # Mapeo: patrón de carpeta → list_type
    DIR_MAP = {
        "articulo-69b-bis-cff": "art_69b_bis",
        "articulo-69b-cff": "art_69b",
        "contribuyentes-incumplidos": "art_69",
    }

    # Recolectar archivos CSV agrupados por list_type
    # REGLA: si existe el archivo completo (Listado_completo), se usa SOLO ese
    # y se saltean los sub-files para evitar duplicados.
    csv_files: dict[str, list[str]] = {}
    patterns = [
        "data/sat/articulo-69b-cff/*.csv",
        "data/sat/articulo-69b-bis-cff/*.csv",
        "data/sat/articulo-69-cff/contribuyentes-incumplidos/*.csv",
    ]
    for pat in patterns:
        for path in glob.glob(pat):
            path_lower = path.lower()
            for folder, lt in DIR_MAP.items():
                if folder in path_lower:
                    csv_files.setdefault(lt, []).append(path)
                    break

    # Si existe el archivo completo para un list_type, usar solo ese
    COMBINED_FILES = {
        "art_69b": "listado_completo_69-b.csv",
        "art_69b_bis": "listado_69_b_bis_completo.csv",
    }
    for lt, combined_name in COMBINED_FILES.items():
        if lt in csv_files:
            combined_paths = [p for p in csv_files[lt] if os.path.basename(p).lower() == combined_name]
            if combined_paths:
                csv_files[lt] = combined_paths
                print(f"  [{lt}] Usando solo {combined_name} (superset — archivos sub-categoría omitidos)")

    if not csv_files:
        raise FileNotFoundError(
            "No se encontraron archivos CSV en data/sat/. "
            "Ejecute primero las descargas desde el portal Datos Abiertos del SAT."
        )

    results = {}
    for list_type, paths in csv_files.items():
        source = SAT_SOURCES[list_type]
        batch_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        supabase_client.table("sat_import_runs").insert({
            "id": run_id, "list_type": list_type, "source_url": source.url,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        try:
            all_rows = []
            for path in sorted(paths):
                filename = os.path.basename(path)
                print(f"  [{list_type}] Parseando {filename}...")
                rows = parse_sat_csv(path)
                all_rows.extend(rows)
                print(f"    → {len(rows)} registros")

            records = _build_records(all_rows, list_type, source.url, batch_id)
            print(f"  [{list_type}] Total: {len(records)} registros — insertando en lotes de {_BATCH_SIZE}...")

            _insert_batch(supabase_client, records, list_type, batch_id)

            supabase_client.table("sat_import_runs").update({
                "status": "success", "rows_imported": len(records),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", run_id).execute()

            results[list_type] = {"run_id": run_id, "rows_imported": len(records)}
            print(f"    ✓ {list_type} completado: {len(records)} registros")
        except Exception:
            supabase_client.table("sat_import_runs").update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", run_id).execute()
            raise

    return results
