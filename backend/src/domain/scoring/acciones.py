ACCIONES_SUGERIDAS = {
    "doc_expired": "Actualizar comprobante de domicilio.",
    "csf_stale": "Solicitar Constancia de Situación Fiscal del mes vigente.",
    "disc_razon_social": "Corregir la razón social para que coincida entre documentos.",
    "disc_rfc": "Verificar y corregir el RFC declarado — no coincide entre documentos.",
    "disc_domicilio": "Conciliar el domicilio entre los documentos del expediente.",
    "disc_representante": "Confirmar el nombre del representante legal entre poder, identificación y formulario.",
    "doc_missing": "Cargar el documento faltante o registrar su metadata manualmente.",
    "rfc_formato_invalido": "Corregir el RFC — no cumple el formato esperado.",
    "sat_69b_definitivo": "No operar — el cliente está en el listado definitivo de EFOS.",
}


def acciones_para(factor_codes: list[str]) -> list[str]:
    vistos = []
    for code in factor_codes:
        accion = ACCIONES_SUGERIDAS.get(code)
        if accion and accion not in vistos:
            vistos.append(accion)
    return vistos
