import hashlib
import uuid
from datetime import datetime, timezone

from src.infrastructure.sat.parsers import parse_art_69, parse_art_69b
from src.infrastructure.sat.sources import SAT_SOURCES

_PARSERS = {"art_69": parse_art_69, "art_69b": parse_art_69b}


def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


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
        records = [{
            "list_type": list_type, "rfc": r["rfc"], "razon_social": r.get("razon_social"),
            "art69b_substate": r.get("art69b_substate"), "situacion": r.get("situacion"),
            "fraccion": r.get("fraccion"),
            "source_url": source.url, "import_batch_id": batch_id,
        } for r in rows]

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
