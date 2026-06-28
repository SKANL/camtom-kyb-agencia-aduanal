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
    "sat_69b_presunto": "RFC en proceso de revisión por presunta emisión de CFDI sin respaldo (Art. 69-B CFF) — iniciar diligencia ampliada y esperar resolución SAT.",
    "sat_69b_bis": "RFC en el listado de transmisión indebida de pérdidas fiscales (Art. 69-B Bis CFF) — solicitar aclaración ante el SAT antes de operar.",
    "sat_69_incumplido": "Contribuyente incumplido (Art. 69 CFF) — requerir aclaración de situación fiscal antes de proceder.",
    "disc_fechas": "Revisar y conciliar las fechas de emisión, vigencia y vencimiento entre los documentos del expediente.",
    "doc_data_incomplete": "Completar los campos obligatorios faltantes en el documento indicado.",
    "manifestacion_incompleta": "Corregir la Manifestación bajo Protesta para incluir la cláusula explícita de los Art. 69-B y 49 Bis CFF.",
    "socios_incompletos": "Registrar todos los socios, accionistas y el beneficiario controlador del acta constitutiva.",
    "rep_legal_incompleto": "Capturar el nombre completo del representante legal en la identificación oficial.",
}


def acciones_para(factor_codes: list[str]) -> list[str]:
    vistos = []
    for code in factor_codes:
        accion = ACCIONES_SUGERIDAS.get(code)
        if accion and accion not in vistos:
            vistos.append(accion)
    return vistos
