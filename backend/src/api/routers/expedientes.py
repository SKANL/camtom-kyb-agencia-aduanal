from fastapi import APIRouter, Depends
from supabase import Client

from api.deps import get_supabase_client
from services.evaluation_service import evaluar_expediente
from services.reconciliation_service import reconciliar_expediente

router = APIRouter()


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
