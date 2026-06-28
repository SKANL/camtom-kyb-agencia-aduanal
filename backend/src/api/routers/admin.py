import os
import tempfile
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
