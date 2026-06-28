from datetime import date
from domain.reconciliation.reconcile import ResultadoConciliacion
from services.evaluation_service import evaluar_expediente

def test_evaluar_expediente_caso_demo_1_limpio(fake_supabase):
    fake_supabase.store["expedientes"] = [{"id": "exp-1", "rfc": "EKU9003173C9"}]
    fake_supabase.store["documentos"] = []
    fake_supabase.store["socios"] = []
    resultado_limpio = ResultadoConciliacion(False, False, False, False, False)
    salida = evaluar_expediente(fake_supabase, "exp-1", resultado_limpio, hoy=date(2026, 6, 28))
    assert salida["decision"] in ("review_required", "high_risk")  # 0 docs → 8 doc_missing (120pts) → high_risk; SAT clean
