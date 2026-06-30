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


def test_evaluar_usa_socios_del_acta_no_de_tabla(fake_supabase):
    """Socios must come from acta.fields.socios, not the unused socios DB table."""
    eid = fake_supabase.make_expediente_id()
    fake_supabase.store["expedientes"] = [{"id": eid, "rfc": "EKU9003173C9"}]
    fake_supabase.store["documentos"] = [
        {
            "id": "doc-acta",
            "expediente_id": eid,
            "doc_type": "acta_constitutiva",
            "extraction_status": "human_reviewed",
            "fields": {"socios": [{"nombre": "Juan Pérez", "porcentaje": 60}]},
        }
    ]
    fake_supabase.store["socios"] = []  # intentionally empty — must NOT be consulted
    fake_supabase.store["sat_lista_registros"] = []
    fake_supabase.store["consultas_sat"] = []
    fake_supabase.store["evaluations"] = []
    from domain.reconciliation.reconcile import ResultadoConciliacion
    resultado = ResultadoConciliacion(False, False, False, False, False)
    salida = evaluar_expediente(fake_supabase, eid, resultado, hoy=date(2026, 6, 30))
    codes = [f["factor_code"] for f in salida["factores_detail"]]
    assert "socios_incompletos" not in codes, (
        f"socios_incompletos fired but socios ARE in acta.fields — evaluation_service "
        f"is reading the empty socios table instead of acta fields. Codes: {codes}"
    )
