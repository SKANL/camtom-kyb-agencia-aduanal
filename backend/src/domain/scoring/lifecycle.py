def necesita_actualizacion(documentos: list[dict], ultima_consulta_sat, hoy, cliente_reporto_cambio: bool) -> bool:
    if cliente_reporto_cambio:
        return True
    if ultima_consulta_sat and (hoy - ultima_consulta_sat).days > 90:
        return True
    for doc in documentos:
        if doc["doc_type"] == "comprobante_domicilio" and doc.get("fecha_emision") and (hoy - doc["fecha_emision"]).days > 90:
            return True
        if doc["doc_type"] == "csf" and doc.get("fecha_emision") and (doc["fecha_emision"].year, doc["fecha_emision"].month) != (hoy.year, hoy.month):
            return True
    return False
