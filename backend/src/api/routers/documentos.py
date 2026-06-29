import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
from pydantic import BaseModel

from api.deps import get_supabase_client
from infrastructure.ai.classify import clasificar_documento
from infrastructure.ai.extract import extraer_campos
from infrastructure.ai.pdf import extraer_texto, extraer_texto_de_bytes
from infrastructure.ai.schemas import SCHEMA_REGISTRY
from infrastructure.storage.supabase_storage import crear_signed_upload_url

router = APIRouter(prefix="/documentos", tags=["documentos"])


class CrearDocumentoBody(BaseModel):
    expediente_id: str
    doc_type: str
    entry_method: str  # "uploaded" | "manual"


@router.get("")
def list_documentos(expediente_id: str, supabase=Depends(get_supabase_client)):
    result = supabase.table("documentos").select("*").eq("expediente_id", expediente_id).execute()
    return result.data


@router.post("")
def crear_documento(body: CrearDocumentoBody, supabase=Depends(get_supabase_client)):
    if body.doc_type not in SCHEMA_REGISTRY:
        raise HTTPException(status_code=422, detail=f"doc_type inválido: {body.doc_type!r}. Valores: {sorted(SCHEMA_REGISTRY)}")
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
    result = supabase.table("documentos").select("*").eq("id", documento_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    doc = result.data[0]
    texto = extraer_texto(doc["storage_path"])
    campos = extraer_campos(supabase, doc["doc_type"], texto)
    supabase.table("documentos").update(
        {"extracted_raw": campos, "fields": campos, "extraction_status": "extracted"}
    ).eq("id", documento_id).execute()
    return {"extraction_status": "extracted", "fields": campos}


@router.patch("/{documento_id}")
def revisar_documento(documento_id: str, fields: dict, supabase=Depends(get_supabase_client)):
    result = supabase.table("documentos").select("id").eq("id", documento_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    supabase.table("documentos").update(
        {"fields": fields, "extraction_status": "human_reviewed"}
    ).eq("id", documento_id).execute()
    return {"extraction_status": "human_reviewed"}


@router.post("/upload")
async def upload_documento(
    expediente_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    supabase=Depends(get_supabase_client),
):
    if not _UUID_RE.match(expediente_id):
        raise HTTPException(status_code=422, detail="expediente_id debe ser un UUID válido")

    if doc_type not in SCHEMA_REGISTRY:
        raise HTTPException(
            status_code=422,
            detail=f"doc_type inválido: {doc_type!r}. Valores: {sorted(SCHEMA_REGISTRY)}",
        )

    existing = (
        supabase.table("documentos")
        .select("id")
        .eq("expediente_id", expediente_id)
        .eq("doc_type", doc_type)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=409,
            detail={"documento_id": existing.data[0]["id"], "message": "Ya existe un documento de este tipo en el expediente"},
        )

    content = await file.read()
    storage_path = f"{expediente_id}/{doc_type}.pdf"

    supabase.storage.from_("kyb-docs").upload(
        path=storage_path,
        file=content,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    texto = extraer_texto_de_bytes(content)
    campos = extraer_campos(supabase, doc_type, texto) if texto.strip() else {}

    documento_id = str(uuid.uuid4())
    supabase.table("documentos").insert(
        {
            "id": documento_id,
            "expediente_id": expediente_id,
            "doc_type": doc_type,
            "entry_method": "uploaded",
            "storage_path": storage_path,
            "extracted_raw": campos,
            "fields": campos,
            "extraction_status": "extracted" if campos else "pending",
        }
    ).execute()

    return {
        "documento_id": documento_id,
        "doc_type": doc_type,
        "fields": campos,
        "extraction_status": "extracted" if campos else "pending",
    }


_CLASSIFY_LABELS = {
    "csf": "Constancia de Situación Fiscal",
    "acta_constitutiva": "Acta Constitutiva",
    "comprobante_domicilio": "Comprobante de Domicilio",
    "identificacion_rep_legal": "ID Representante Legal",
    "poder_notarial": "Poder Notarial",
    "encargo_conferido": "Encargo Conferido",
    "manifestacion_protesta": "Manifestación bajo Protesta",
    "unknown": "Sin clasificar",
}


_MAX_CLASSIFY_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/classify")
async def classify_documento(file: UploadFile = File(...)):
    """Classify a PDF by content without creating a DB record."""
    content = await file.read(_MAX_CLASSIFY_BYTES + 1)
    if len(content) > _MAX_CLASSIFY_BYTES:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 10 MB)")
    texto = extraer_texto_de_bytes(content)
    if not texto.strip():
        return {"doc_type": "unknown", "confidence": "low", "suggested_label": "Sin texto extraído"}
    result = clasificar_documento(texto)
    return {
        "doc_type": result["doc_type"],
        "confidence": result["confidence"],
        "suggested_label": _CLASSIFY_LABELS.get(result["doc_type"], "Sin clasificar"),
    }
