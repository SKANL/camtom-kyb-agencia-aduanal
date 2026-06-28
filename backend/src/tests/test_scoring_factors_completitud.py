from datetime import date
from domain.scoring.factors import factores_completitud

def test_doc_missing_por_cada_tipo_ausente():
    factores = factores_completitud([], [], date(2026, 6, 28))
    assert [f.factor_code for f in factores].count("doc_missing") == 8

def test_comprobante_domicilio_vencido():
    documentos = [{"id": "1", "doc_type": "comprobante_domicilio", "extraction_status": "human_reviewed", "fields": {"domicilio": "x"}, "fecha_emision": date(2026, 1, 1)}]
    assert any(f.factor_code == "doc_expired" for f in factores_completitud(documentos, [], date(2026, 6, 28)))

def test_csf_fuera_de_mes_vigente():
    documentos = [{"id": "1", "doc_type": "csf", "extraction_status": "human_reviewed", "fields": {"rfc": "x"}, "fecha_emision": date(2026, 5, 1)}]
    assert any(f.factor_code == "csf_stale" for f in factores_completitud(documentos, [], date(2026, 6, 28)))

def test_acta_presente_sin_socios_dispara_socios_incompletos():
    documentos = [{"id": "1", "doc_type": "acta_constitutiva", "extraction_status": "human_reviewed", "fields": {"razon_social": "x"}, "fecha_emision": None}]
    assert any(f.factor_code == "socios_incompletos" for f in factores_completitud(documentos, [], date(2026, 6, 28)))
