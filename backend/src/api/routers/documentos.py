import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_supabase_client
from infrastructure.ai.extract import extraer_campos
from infrastructure.ai.pdf import extraer_texto
from infrastructure.storage.supabase_storage import crear_signed_upload_url

router = APIRouter(prefix="/documentos", tags=["documentos"])


class CrearDocumentoBody(BaseModel):
    expediente_id: str
    doc_type: str
    entry_method: str  # "uploaded" | "manual"


@router.post("")
def crear_documento(body: CrearDocumentoBody, supabase=Depends(get_supabase_client)):
    documento_id = str(uuid.uuid4())
    path = f"{body.expediente_id}/{body.doc_type}.pdf" if body.entry_method == "uploaded" else None
    supabase.table("documentos").insert(
        {
            "id": documento_id,
            "expediente_id": body.expediente_id,
            "doc_type": body.doc_type,
            "entry_method": body.entry_method,
            "storage_path": path,
            "extraction_status": "pending" if body.entry_method == "uploaded" else "not_applicable",
        }
    ).execute()
    if body.entry_method == "manual":
        return {"documento_id": documento_id}
    return {"documento_id": documento_id, **crear_signed_upload_url(supabase, path)}


@router.post("/{documento_id}/extract")
def extract_documento(documento_id: str, supabase=Depends(get_supabase_client)):
    doc = supabase.table("documentos").select("*").eq("id", documento_id).execute().data[0]
    texto = extraer_texto(doc["storage_path"])
    campos = extraer_campos(supabase, doc["doc_type"], texto)
    supabase.table("documentos").update(
        {"extracted_raw": campos, "fields": campos, "extraction_status": "extracted"}
    ).eq("id", documento_id).execute()
    return {"extraction_status": "extracted", "fields": campos}


@router.patch("/{documento_id}")
def revisar_documento(documento_id: str, fields: dict, supabase=Depends(get_supabase_client)):
    supabase.table("documentos").update(
        {"fields": fields, "extraction_status": "human_reviewed"}
    ).eq("id", documento_id).execute()
    return {"extraction_status": "human_reviewed"}
