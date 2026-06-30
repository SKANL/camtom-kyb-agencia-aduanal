from datetime import date
from domain.scoring.factors import factores_completitud

def test_doc_missing_por_cada_tipo_ausente():
    factores = factores_completitud([], [], date(2026, 6, 28))
    assert [f.factor_code for f in factores].count("doc_missing") == 8

def test_comprobante_domicilio_vencido():
    documentos = [{"id": "1", "doc_type": "comprobante_domicilio", "extraction_status": "human_reviewed", "fields": {"domicilio": "x", "fecha_emision": "2026-01-01"}}]
    assert any(f.factor_code == "doc_expired" for f in factores_completitud(documentos, [], date(2026, 6, 28)))

def test_csf_fuera_de_mes_vigente():
    documentos = [{"id": "1", "doc_type": "csf", "extraction_status": "human_reviewed", "fields": {"rfc": "x", "fecha_emision": "2026-05-01"}}]
    assert any(f.factor_code == "csf_stale" for f in factores_completitud(documentos, [], date(2026, 6, 28)))

def test_acta_presente_sin_socios_dispara_socios_incompletos():
    documentos = [{"id": "1", "doc_type": "acta_constitutiva", "extraction_status": "human_reviewed", "fields": {"razon_social": "x"}}]
    assert any(f.factor_code == "socios_incompletos" for f in factores_completitud(documentos, [], date(2026, 6, 28)))


def _make_doc(doc_type, fields=None, status="human_reviewed"):
    return {
        "id": "test-id",
        "doc_type": doc_type,
        "extraction_status": status,
        "fields": fields or {},
    }

def test_doc_expired_fires_when_fecha_in_fields():
    """comprobante_domicilio with fecha_emision > 90 days ago in fields should fire doc_expired."""
    all_doc_types = [
        "acta_constitutiva", "identificacion_rep_legal", "poder_notarial",
        "encargo_conferido", "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
    ]
    docs = [_make_doc(t) for t in all_doc_types if t != "comprobante_domicilio"]
    old_date = "2025-01-01"
    docs.append(_make_doc("comprobante_domicilio", {"fecha_emision": old_date}))
    hoy = date(2026, 6, 29)
    factores = factores_completitud(docs, [], hoy)
    codes = [f.factor_code for f in factores]
    assert "doc_expired" in codes, f"Expected doc_expired in {codes}"

def test_doc_expired_does_not_fire_for_recent_comprobante():
    all_doc_types = [
        "acta_constitutiva", "identificacion_rep_legal", "poder_notarial",
        "encargo_conferido", "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
    ]
    docs = [_make_doc(t) for t in all_doc_types if t != "comprobante_domicilio"]
    docs.append(_make_doc("comprobante_domicilio", {"fecha_emision": "2026-06-01"}))
    hoy = date(2026, 6, 29)
    factores = factores_completitud(docs, [], hoy)
    codes = [f.factor_code for f in factores]
    assert "doc_expired" not in codes

def test_csf_stale_fires_when_fecha_in_fields():
    """CSF with fecha_emision from last month should fire csf_stale."""
    all_doc_types = [
        "acta_constitutiva", "identificacion_rep_legal", "poder_notarial",
        "encargo_conferido", "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
    ]
    docs = [_make_doc(t) for t in all_doc_types if t != "csf"]
    docs.append(_make_doc("csf", {"fecha_emision": "2026-05-01"}))
    hoy = date(2026, 6, 29)
    factores = factores_completitud(docs, [], hoy)
    codes = [f.factor_code for f in factores]
    assert "csf_stale" in codes, f"Expected csf_stale in {codes}"

def test_csf_stale_does_not_fire_for_current_month():
    all_doc_types = [
        "acta_constitutiva", "identificacion_rep_legal", "poder_notarial",
        "encargo_conferido", "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
    ]
    docs = [_make_doc(t) for t in all_doc_types if t != "csf"]
    docs.append(_make_doc("csf", {"fecha_emision": "2026-06-01"}))
    hoy = date(2026, 6, 29)
    factores = factores_completitud(docs, [], hoy)
    codes = [f.factor_code for f in factores]
    assert "csf_stale" not in codes


def test_manifestacion_true_no_penalty():
    """declara_no_69b_49bis=True → manifestacion_incompleta must NOT fire."""
    docs = [_make_doc("manifestacion_protesta", {"declara_no_69b_49bis": True})]
    hoy = date(2026, 6, 30)
    codes = [f.factor_code for f in factores_completitud(docs, [{"nombre": "x"}], hoy)]
    assert "manifestacion_incompleta" not in codes, f"Should NOT fire with True: {codes}"


def test_manifestacion_false_fires_penalty():
    """declara_no_69b_49bis=False → manifestacion_incompleta must fire."""
    docs = [_make_doc("manifestacion_protesta", {"declara_no_69b_49bis": False})]
    hoy = date(2026, 6, 30)
    codes = [f.factor_code for f in factores_completitud(docs, [{"nombre": "x"}], hoy)]
    assert "manifestacion_incompleta" in codes, f"Should fire with False: {codes}"


def test_manifestacion_none_no_penalty():
    """declara_no_69b_49bis=None (AI uncertain) → manifestacion_incompleta must NOT fire.
    Only explicit False (declared non-compliant) triggers the penalty. Uncertain (None) means
    the AI couldn't parse the clause — we don't penalize for AI uncertainty."""
    docs = [_make_doc("manifestacion_protesta", {"declara_no_69b_49bis": None})]
    hoy = date(2026, 6, 30)
    codes = [f.factor_code for f in factores_completitud(docs, [{"nombre": "x"}], hoy)]
    assert "manifestacion_incompleta" not in codes, f"Should NOT fire with None: {codes}"


def test_doc_data_incomplete_ignores_optional_fields():
    """Optional fields returning None (e.g. regimen_fiscal) must NOT trigger doc_data_incomplete."""
    doc = _make_doc("csf", {
        "rfc": "EKU9003173C9",
        "razon_social": "Escuela Kemper Urgate SA de CV",
        "regimen_fiscal": None,    # optional — AI couldn't extract
        "domicilio_fiscal": None,  # optional
        "fecha_emision": "2026-06-30",
    })
    codes = [f.factor_code for f in factores_completitud([doc], [], date(2026, 6, 30))]
    assert "doc_data_incomplete" not in codes, (
        f"doc_data_incomplete must not fire when only optional fields are null; got {codes}"
    )


def test_doc_data_incomplete_fires_for_required_missing():
    """Missing rfc (required for csf) MUST trigger doc_data_incomplete."""
    doc = _make_doc("csf", {
        "rfc": None,
        "razon_social": "Escuela Kemper Urgate SA de CV",
        "fecha_emision": "2026-06-30",
    })
    codes = [f.factor_code for f in factores_completitud([doc], [], date(2026, 6, 30))]
    assert "doc_data_incomplete" in codes, (
        f"doc_data_incomplete must fire when required field rfc is null; got {codes}"
    )


def test_doc_data_incomplete_unknown_doc_type_no_fire():
    """Unknown doc types have no required fields — must not fire doc_data_incomplete."""
    doc = _make_doc("unknown_type", {"campo": None})
    codes = [f.factor_code for f in factores_completitud([doc], [], date(2026, 6, 30))]
    assert "doc_data_incomplete" not in codes
