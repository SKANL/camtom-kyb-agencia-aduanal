from domain.scoring.acciones import acciones_para


def test_acciones_para_caso_demo_2_en_orden_sin_duplicar():
    acciones = acciones_para(["disc_razon_social", "doc_expired", "disc_razon_social"])
    assert acciones == ["Corregir la razón social para que coincida entre documentos.", "Actualizar comprobante de domicilio."]
