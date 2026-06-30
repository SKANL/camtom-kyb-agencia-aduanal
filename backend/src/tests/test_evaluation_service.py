from datetime import date
from domain.reconciliation.reconcile import ResultadoConciliacion
from services.evaluation_service import evaluar_expediente


def _make_all_docs(expediente_id: str, *, rfc: str, razon_social: str, rep_legal: str,
                   manifestacion_declara: bool | None = True) -> list[dict]:
    """Create 8 human-reviewed documents for a complete clean expediente."""
    from datetime import date
    return [
        {
            "id": f"doc-csf-{expediente_id}",
            "expediente_id": expediente_id,
            "doc_type": "csf",
            "extraction_status": "human_reviewed",
            "fields": {
                "rfc": rfc,
                "razon_social": razon_social,
                "fecha_emision": date.today().isoformat(),
            },
        },
        {
            "id": f"doc-acta-{expediente_id}",
            "expediente_id": expediente_id,
            "doc_type": "acta_constitutiva",
            "extraction_status": "human_reviewed",
            "fields": {
                "rfc": rfc,
                "razon_social": razon_social,
                "socios": [{"nombre": rep_legal, "porcentaje": 100}],
            },
        },
        {
            "id": f"doc-comp-{expediente_id}",
            "expediente_id": expediente_id,
            "doc_type": "comprobante_domicilio",
            "extraction_status": "human_reviewed",
            "fields": {"fecha_emision": date.today().isoformat()},
        },
        {
            "id": f"doc-manif-{expediente_id}",
            "expediente_id": expediente_id,
            "doc_type": "manifestacion_protesta",
            "extraction_status": "human_reviewed",
            "fields": {"declara_no_69b_49bis": manifestacion_declara},
        },
        {
            "id": f"doc-iden-{expediente_id}",
            "expediente_id": expediente_id,
            "doc_type": "identificacion_rep_legal",
            "extraction_status": "human_reviewed",
            "fields": {"nombre_completo": rep_legal},
        },
        {
            "id": f"doc-poder-{expediente_id}",
            "expediente_id": expediente_id,
            "doc_type": "poder_notarial",
            "extraction_status": "human_reviewed",
            "fields": {"nombre_representante": rep_legal},
        },
        {
            "id": f"doc-enc-{expediente_id}",
            "expediente_id": expediente_id,
            "doc_type": "encargo_conferido",
            "extraction_status": "human_reviewed",
            "fields": {"rfc_agente_aduanal": "CAMT930401AB9"},
        },
        {
            "id": f"doc-rfc-{expediente_id}",
            "expediente_id": expediente_id,
            "doc_type": "rfc",
            "extraction_status": "human_reviewed",
            "fields": {"rfc": rfc, "razon_social": razon_social},
        },
    ]


def test_scenario_1_safe(fake_supabase):
    """Scenario 1: clean expediente with all docs + no SAT hits → safe."""
    from datetime import date
    from domain.reconciliation.reconcile import ResultadoConciliacion
    eid = fake_supabase.make_expediente_id()
    fake_supabase.store["expedientes"] = [
        {"id": eid, "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV"}
    ]
    fake_supabase.store["documentos"] = _make_all_docs(
        eid, rfc="EKU9003173C9",
        razon_social="Escuela Kemper Urgate SA de CV",
        rep_legal="Juan Pérez García",
        manifestacion_declara=True,  # has the 69-B/49-Bis clauses
    )
    fake_supabase.store["sat_lista_registros"] = []  # RFC not in any SAT list
    fake_supabase.store["consultas_sat"] = []
    fake_supabase.store["evaluations"] = []

    resultado = ResultadoConciliacion(
        rfc_discrepante=False,
        razon_social_discrepante=False,
        domicilio_discrepante=False,
        representante_discrepante=False,
        fechas_inconsistentes=False,
    )
    salida = evaluar_expediente(fake_supabase, eid, resultado, hoy=date(2026, 6, 30))
    assert salida["decision"] == "safe", (
        f"Scenario 1 should be 'safe' but got '{salida['decision']}' "
        f"(score={salida['score_total']}, "
        f"factors={[f['factor_code'] for f in salida['factores_detail'] if f['points'] > 0]})"
    )
    assert salida["score_total"] == 0, (
        f"Score should be 0 but got {salida['score_total']}. "
        f"Non-zero factors: {[f for f in salida['factores_detail'] if f['points'] > 0]}"
    )


def test_scenario_2_review_required(fake_supabase):
    """Scenario 2: disc_razon_social (30) + disc_representante (25) = 55 → review_required."""
    from datetime import date
    from domain.reconciliation.reconcile import ResultadoConciliacion
    eid = fake_supabase.make_expediente_id()
    fake_supabase.store["expedientes"] = [
        {"id": eid, "rfc": "COX010101ABA", "razon_social": "Corporativo X SA de CV"}
    ]
    fake_supabase.store["documentos"] = _make_all_docs(
        eid, rfc="COX010101ABA",
        razon_social="Corporativo X SA de CV",
        rep_legal="Maria Lopez Hernandez",
        manifestacion_declara=True,
    )
    fake_supabase.store["sat_lista_registros"] = []
    fake_supabase.store["consultas_sat"] = []
    fake_supabase.store["evaluations"] = []

    resultado = ResultadoConciliacion(
        rfc_discrepante=False,
        razon_social_discrepante=True,   # "Corporativo Equis Distribuidora" vs "Corporativo X"
        domicilio_discrepante=False,
        representante_discrepante=True,  # "Carlos Eduardo Morales Ríos" vs "Maria Lopez"
        fechas_inconsistentes=False,
    )
    salida = evaluar_expediente(fake_supabase, eid, resultado, hoy=date(2026, 6, 30))
    assert salida["decision"] == "review_required", (
        f"Scenario 2 should be 'review_required' but got '{salida['decision']}' "
        f"(score={salida['score_total']})"
    )
    assert 30 <= salida["score_total"] <= 69, (
        f"Score should be in 30–69 range but got {salida['score_total']}. "
        f"Factors: {[(f['factor_code'], f['points']) for f in salida['factores_detail'] if f['points'] > 0]}"
    )


def test_scenario_3_high_risk(fake_supabase):
    """Scenario 3: RFC in Art. 69-B definitivos → critical_block → high_risk regardless of score."""
    from datetime import date
    from domain.reconciliation.reconcile import ResultadoConciliacion
    eid = fake_supabase.make_expediente_id()
    fake_supabase.store["expedientes"] = [
        {"id": eid, "rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV"}
    ]
    fake_supabase.store["documentos"] = _make_all_docs(
        eid, rfc="AAA120730823",
        razon_social="Empresa en Lista Negra SA de CV",
        rep_legal="Carlos Sánchez",
        manifestacion_declara=None,  # incomplete — doesn't have the 69-B clauses
    )
    # RFC in Art. 69-B definitivos — field name is art69b_substate (DB column), not match_substate
    fake_supabase.store["sat_lista_registros"] = [
        {
            "id": "sat-1",
            "rfc": "AAA120730823",
            "list_type": "art_69b",
            "art69b_substate": "definitivo",
            "razon_social": "EMPRESA EN LISTA NEGRA SA DE CV",
        }
    ]
    fake_supabase.store["consultas_sat"] = []
    fake_supabase.store["evaluations"] = []

    resultado = ResultadoConciliacion(False, False, False, False, False)
    salida = evaluar_expediente(fake_supabase, eid, resultado, hoy=date(2026, 6, 30))
    assert salida["decision"] == "high_risk", (
        f"Scenario 3 should be 'high_risk' but got '{salida['decision']}'"
    )
    critical = [f["factor_code"] for f in salida["factores_detail"] if f["is_critical_block"]]
    assert "sat_69b_definitivo" in critical, (
        f"sat_69b_definitivo should be a critical block but got: {critical}"
    )

def test_evaluar_expediente_caso_demo_1_limpio(fake_supabase):
    fake_supabase.store["expedientes"] = [{"id": "exp-1", "rfc": "EKU9003173C9"}]
    fake_supabase.store["documentos"] = []
    fake_supabase.store["socios"] = []
    resultado_limpio = ResultadoConciliacion(False, False, False, False, False)
    salida = evaluar_expediente(fake_supabase, "exp-1", resultado_limpio, hoy=date(2026, 6, 28))
    assert salida["decision"] in ("review_required", "high_risk")  # 0 docs → 8 doc_missing (120pts) → high_risk; SAT clean


def test_factores_informativos_separated_from_scored(fake_supabase):
    """art_49bis_no_verificable must be in factores_informativos, not factores_detail."""
    from datetime import date
    from domain.reconciliation.reconcile import ResultadoConciliacion
    eid = fake_supabase.make_expediente_id()
    fake_supabase.store["expedientes"] = [
        {"id": eid, "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV"}
    ]
    fake_supabase.store["documentos"] = []
    fake_supabase.store["sat_lista_registros"] = []
    fake_supabase.store["consultas_sat"] = []
    fake_supabase.store["evaluations"] = []
    resultado = ResultadoConciliacion(False, False, False, False, False)
    salida = evaluar_expediente(fake_supabase, eid, resultado, hoy=date(2026, 6, 30))

    scored_codes = [f["factor_code"] for f in salida["factores_detail"]]
    info_codes = [f["factor_code"] for f in salida.get("factores_informativos", [])]

    assert "art_49bis_no_verificable" not in scored_codes, (
        f"art_49bis_no_verificable must not appear in factores_detail; got: {scored_codes}"
    )
    assert "art_49bis_no_verificable" in info_codes, (
        f"art_49bis_no_verificable must appear in factores_informativos; got: {info_codes}"
    )
    assert "factores_informativos" in salida


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
