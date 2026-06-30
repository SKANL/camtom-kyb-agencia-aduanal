"""End-to-end scenario tests for the KYB scoring pipeline.

Calls factores_* + evaluar() directly with synthetic data that mirrors what
the 3 demo scenarios produce after correct AI extraction and human review.

Scenario 1 — CLEAN (EKU9003173C9): score 0 → safe
Scenario 2 — DISCREPANCY (COX010101AB1): disc_razon_social(30) + disc_representante(25) = 55 → review_required
Scenario 3 — HIGH RISK (AAA120730823): sat_69b_definitivo(100, critical) → high_risk
"""
from datetime import date

from domain.reconciliation.reconcile import ResultadoConciliacion
from domain.scoring.engine import evaluar
from domain.scoring.factors import Factor, factores_completitud, factores_discrepancias, factores_listas_sat

HOY = date(2026, 6, 30)

_CLEAN_RECONCILIACION = ResultadoConciliacion(
    rfc_discrepante=False,
    razon_social_discrepante=False,
    domicilio_discrepante=False,
    representante_discrepante=False,
    fechas_inconsistentes=False,
)


def _make_doc(doc_type, fields=None, status="human_reviewed"):
    return {"id": f"{doc_type}-id", "doc_type": doc_type,
            "extraction_status": status, "fields": fields or {}}


# ── Scenario 1: CLEAN ──────────────────────────────────────────────────────────

SCENARIO_1_DOCS = [
    _make_doc("csf", {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV",
                      "fecha_emision": "2026-06-01"}),
    _make_doc("acta_constitutiva", {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV",
              "socios": [{"nombre": "Juan Pérez García", "rfc": "PEGJ850101HDFRZN09", "porcentaje": 60},
                         {"nombre": "María López Ramírez", "rfc": "LOPM760315MDFPRR08", "porcentaje": 40}]}),
    _make_doc("comprobante_domicilio", {"domicilio": "Av. Insurgentes Sur 123", "fecha_emision": "2026-06-01"}),
    _make_doc("identificacion_rep_legal", {"nombre_completo": "Juan Pérez García", "fecha_vencimiento": "2029-12-31"}),
    _make_doc("poder_notarial", {"nombre_representante": "Juan Pérez García", "alcance": "Actos de Administración"}),
    _make_doc("encargo_conferido", {"rfc_agente_aduanal": "CAMT930401AB9", "alcance": "Import/Export",
                                    "fecha_vigencia": "2027-12-31"}),
    _make_doc("manifestacion_protesta", {"declara_no_69b_49bis": True}),
    _make_doc("rfc", {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV",
                      "domicilio_fiscal": "Av. Insurgentes Sur 123"}),
]
SCENARIO_1_SOCIOS = [
    {"nombre": "Juan Pérez García", "rfc": "PEGJ850101HDFRZN09", "porcentaje": 60},
    {"nombre": "María López Ramírez", "rfc": "LOPM760315MDFPRR08", "porcentaje": 40},
]


def test_scenario_1_clean_is_safe():
    """Scenario 1 (EKU9003173C9): RFC not in SAT lists, all docs complete → safe."""
    all_factors = (
        factores_listas_sat([])  # no SAT hits
        + factores_discrepancias(_CLEAN_RECONCILIACION)
        + factores_completitud(SCENARIO_1_DOCS, SCENARIO_1_SOCIOS, HOY)
    )
    resultado = evaluar(all_factors)
    penalty_factors = [f for f in all_factors if f.points > 0]
    assert not penalty_factors, (
        f"Scenario 1 must have zero penalty factors; got "
        f"{[(f.factor_code, f.points) for f in penalty_factors]}"
    )
    assert resultado.decision == "safe", (
        f"Scenario 1 must be safe; got {resultado.decision} (score={resultado.score_total})"
    )
    assert resultado.score_total == 0


def test_scenario_1_art_49bis_is_informational_only():
    """art_49bis_no_verificable always fires but with 0 points — must not affect decision."""
    all_factors = factores_listas_sat([])
    informational = [f for f in all_factors if f.factor_code == "art_49bis_no_verificable"]
    assert informational, "art_49bis_no_verificable must always be present"
    assert informational[0].points == 0
    assert not informational[0].is_critical_block


# ── Scenario 2: DISCREPANCY ────────────────────────────────────────────────────

_DISC_RECONCILIACION = ResultadoConciliacion(
    rfc_discrepante=False,
    razon_social_discrepante=True,
    domicilio_discrepante=False,
    representante_discrepante=True,
    fechas_inconsistentes=False,
    compared_values={
        "razon_social": {
            "expediente": "Corporativo Equis Distribuidora, SA de CV",
            "documento": "Corporativo X, S.A. de C.V.",
        },
        "representante": {
            "expediente": "María López",
            "documento": "Carlos Eduardo Morales Ríos",
        },
    },
)

SCENARIO_2_DOCS = [
    _make_doc("csf", {"rfc": "COX010101AB1", "razon_social": "Corporativo Equis Distribuidora, SA de CV",
                      "fecha_emision": "2026-06-01"}),
    _make_doc("acta_constitutiva", {"rfc": "COX010101AB1", "razon_social": "Corporativo X, S.A. de C.V.",
              "socios": [{"nombre": "María López Hernandez", "rfc": "LOHM780315MDFPRR08", "porcentaje": 51}]}),
    _make_doc("comprobante_domicilio", {"domicilio": "Insurgentes Sur 123", "fecha_emision": "2026-06-01"}),
    _make_doc("identificacion_rep_legal", {"nombre_completo": "Maria Lopez Hernandez",
                                           "fecha_vencimiento": "2029-12-31"}),
    _make_doc("poder_notarial", {"nombre_representante": "Carlos Eduardo Morales Ríos", "alcance": "Admin."}),
    _make_doc("encargo_conferido", {"rfc_agente_aduanal": "CAMT930401AB9", "alcance": "Import/Export",
                                    "fecha_vigencia": "2027-12-31"}),
    _make_doc("manifestacion_protesta", {"declara_no_69b_49bis": True}),
    _make_doc("rfc", {"rfc": "COX010101AB1", "razon_social": "Corporativo X SA de CV",
                      "domicilio_fiscal": "Insurgentes Sur 123"}),
]
SCENARIO_2_SOCIOS = [{"nombre": "María López Hernandez", "rfc": "LOHM780315MDFPRR08", "porcentaje": 51}]


def test_scenario_2_discrepancy_is_review_required():
    """Scenario 2 (COX010101AB1): razon_social + representante mismatch → 30+25=55 → review_required."""
    all_factors = (
        factores_listas_sat([])
        + factores_discrepancias(_DISC_RECONCILIACION)
        + factores_completitud(SCENARIO_2_DOCS, SCENARIO_2_SOCIOS, HOY)
    )
    resultado = evaluar(all_factors)
    codes = [f.factor_code for f in all_factors]
    assert "disc_razon_social" in codes, f"disc_razon_social must fire; got {codes}"
    assert "disc_representante" in codes, f"disc_representante must fire; got {codes}"
    assert resultado.decision == "review_required", (
        f"Scenario 2 must be review_required; got {resultado.decision} (score={resultado.score_total})"
    )
    assert 30 <= resultado.score_total < 70, (
        f"Scenario 2 score must be in [30, 69]; got {resultado.score_total}"
    )


# ── Scenario 3: HIGH RISK ──────────────────────────────────────────────────────

SCENARIO_3_SAT_HITS = [
    {"factor_code": "sat_69b_definitivo", "list_type": "art_69b",
     "match_substate": "definitivo", "rfc": "AAA120730823"},
]
SCENARIO_3_DOCS = [
    _make_doc("csf", {"rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV",
                      "fecha_emision": "2026-06-01"}),
    _make_doc("acta_constitutiva", {"rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV",
              "socios": [{"nombre": "Carlos Sánchez", "rfc": "SANC720410HDFNCR06", "porcentaje": 100}]}),
    _make_doc("comprobante_domicilio", {"domicilio": "Calle Reforma 456", "fecha_emision": "2026-06-01"}),
    _make_doc("identificacion_rep_legal", {"nombre_completo": "Carlos Sánchez",
                                           "fecha_vencimiento": "2029-12-31"}),
    _make_doc("poder_notarial", {"nombre_representante": "Carlos Sánchez", "alcance": "Admin."}),
    _make_doc("encargo_conferido", {"rfc_agente_aduanal": "CAMT930401AB9", "alcance": "Import/Export",
                                    "fecha_vigencia": "2027-12-31"}),
    _make_doc("manifestacion_protesta", {"declara_no_69b_49bis": False}),  # explicitly non-compliant
    _make_doc("rfc", {"rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV",
                      "domicilio_fiscal": "Calle Reforma 456"}),
]
SCENARIO_3_SOCIOS = [{"nombre": "Carlos Sánchez", "rfc": "SANC720410HDFNCR06", "porcentaje": 100}]


def test_scenario_3_high_risk_sat_69b_definitivo():
    """Scenario 3 (AAA120730823): RFC in 69-B definitivos → critical block → high_risk."""
    all_factors = (
        factores_listas_sat(SCENARIO_3_SAT_HITS)
        + factores_discrepancias(_CLEAN_RECONCILIACION)
        + factores_completitud(SCENARIO_3_DOCS, SCENARIO_3_SOCIOS, HOY)
    )
    resultado = evaluar(all_factors)
    assert resultado.decision == "high_risk", (
        f"Scenario 3 must be high_risk due to critical block; got {resultado.decision}"
    )
    assert "sat_69b_definitivo" in resultado.critical_blocks
    codes = [f.factor_code for f in all_factors]
    assert "manifestacion_incompleta" in codes, (
        "manifestacion_incompleta must fire for scenario 3 (declara_no_69b_49bis=False)"
    )


# ── Score boundary tests ───────────────────────────────────────────────────────

def test_score_29_is_safe():
    assert evaluar([Factor("doc_missing", 29, False, "test")]).decision == "safe"


def test_score_30_is_review_required():
    assert evaluar([Factor("doc_missing", 30, False, "test")]).decision == "review_required"


def test_score_69_is_review_required():
    assert evaluar([Factor("doc_missing", 69, False, "test")]).decision == "review_required"


def test_score_70_is_high_risk():
    assert evaluar([Factor("doc_missing", 70, False, "test")]).decision == "high_risk"


def test_critical_block_forces_high_risk_at_any_score():
    """Critical block → high_risk even with a score that would normally be review_required."""
    resultado = evaluar([Factor("sat_69b_definitivo", 40, True, "EFOS definitivo")])
    assert resultado.decision == "high_risk"
    assert "sat_69b_definitivo" in resultado.critical_blocks
