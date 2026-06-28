import os
import tempfile
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, Depends
from src.api.deps import get_supabase_client
from src.infrastructure.sat.ingest import ingest_list

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sat/ingest/{list_type}")
async def ingest_sat_list(list_type: str, file: UploadFile, supabase=Depends(get_supabase_client)):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        return ingest_list(supabase, list_type, tmp_path)
    finally:
        os.unlink(tmp_path)


@router.get("/sat-import-runs")
def list_sat_import_runs(supabase=Depends(get_supabase_client)):
    result = (
        supabase.table("sat_import_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(50)
        .execute()
    )
    return result.data


@router.post("/ingest/{list_type}")
def trigger_ingest_demo(list_type: str, supabase=Depends(get_supabase_client)):
    """Demo endpoint — records an import run without requiring file upload."""
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    run = {
        "id": run_id,
        "list_type": list_type,
        "status": "completed",
        "rows_imported": 0,
        "started_at": now,
        "finished_at": now,
    }
    supabase.table("sat_import_runs").insert(run).execute()
    return run
