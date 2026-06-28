from datetime import date
from domain.scoring.lifecycle import necesita_actualizacion

def test_cliente_reporta_cambio_siempre_dispara_needs_update():
    assert necesita_actualizacion([], None, date(2026, 6, 28), cliente_reporto_cambio=True) is True

def test_comprobante_vencido_dispara_needs_update():
    documentos = [{"doc_type": "comprobante_domicilio", "fecha_emision": date(2026, 1, 1)}]
    assert necesita_actualizacion(documentos, None, date(2026, 6, 28), cliente_reporto_cambio=False) is True

def test_expediente_limpio_no_necesita_actualizacion():
    documentos = [{"doc_type": "comprobante_domicilio", "fecha_emision": date(2026, 6, 1)}]
    assert necesita_actualizacion(documentos, date(2026, 6, 1), date(2026, 6, 28), cliente_reporto_cambio=False) is False
