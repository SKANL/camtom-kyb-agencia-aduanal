from fastapi import APIRouter, Depends
from supabase import Client
from api.deps import get_supabase_client
from domain.reconciliation.reconcile import ResultadoConciliacion
from services.evaluation_service import evaluar_expediente

router = APIRouter()

@router.post("/{expediente_id}/evaluate")
async def evaluate_expediente(
    expediente_id: str,
    supabase: Client = Depends(get_supabase_client),
):
    # Fase 3 stub: ResultadoConciliacion inyectado como "limpio" hasta que Task 4.5 conecte la IA real.
    resultado_reconciliacion = ResultadoConciliacion(False, False, False, False, False)
    return evaluar_expediente(supabase, expediente_id, resultado_reconciliacion)
