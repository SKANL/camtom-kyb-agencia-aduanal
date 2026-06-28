import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client

from api.deps import get_supabase_client
from services.evaluation_service import evaluar_expediente
from services.reconciliation_service import reconciliar_expediente

router = APIRouter()


class CrearExpedienteBody(BaseModel):
    razon_social: str
    rfc: str
    domicilio_fiscal: str = ""
    representante_legal: str = ""


@router.get("")
def list_expedientes(supabase: Client = Depends(get_supabase_client)):
    result = supabase.table("expedientes").select("*").order("created_at", desc=True).execute()
    return result.data


@router.post("")
def crear_expediente(body: CrearExpedienteBody, supabase: Client = Depends(get_supabase_client)):
    expediente_id = str(uuid.uuid4())
    data = {
        "id": expediente_id,
        "razon_social": body.razon_social,
        "rfc": body.rfc.upper(),
        "domicilio_fiscal": body.domicilio_fiscal,
        "representante_legal": body.representante_legal,
        "status": "pending",
        "decision": None,
        "score_total": None,
    }
    result = supabase.table("expedientes").insert(data).execute()
    return result.data[0]


@router.get("/{expediente_id}/evaluations/latest")
def get_latest_evaluation(expediente_id: str, supabase: Client = Depends(get_supabase_client)):
    result = (
        supabase.table("evaluations")
        .select("*")
        .eq("expediente_id", expediente_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    return {
        "decision": row["decision"],
        "score_total": row["score_total"],
        "factores_score": {code: 100 for code in (row.get("critical_blocks") or [])},
        "acciones_sugeridas": (row.get("summary") or {}).get("acciones_sugeridas", []),
        "evaluated_at": row["created_at"],
    }


@router.get("/{expediente_id}/consultas-sat")
def get_consultas_sat(expediente_id: str, supabase: Client = Depends(get_supabase_client)):
    result = (
        supabase.table("consultas_sat")
        .select("*")
        .eq("expediente_id", expediente_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/{expediente_id}")
def get_expediente(expediente_id: str, supabase: Client = Depends(get_supabase_client)):
    result = supabase.table("expedientes").select("*").eq("id", expediente_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return result.data[0]


@router.post("/{expediente_id}/evaluate")
def evaluate_expediente(
    expediente_id: str,
    supabase: Client = Depends(get_supabase_client),
):
    resultado_reconciliacion = reconciliar_expediente(supabase, expediente_id)
    return evaluar_expediente(supabase, expediente_id, resultado_reconciliacion)


@router.post("/{expediente_id}/report-change")
def report_change(
    expediente_id: str,
    reason: str,
    supabase: Client = Depends(get_supabase_client),
):
    supabase.table("expedientes").update(
        {"status": "needs_update", "needs_update_reason": reason}
    ).eq("id", expediente_id).execute()
    supabase.table("audit_log").insert(
        {"expediente_id": expediente_id, "event_type": "report_change", "payload": {"reason": reason}}
    ).execute()
    return {"status": "needs_update"}
