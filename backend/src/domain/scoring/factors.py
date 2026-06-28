from dataclasses import dataclass

@dataclass(frozen=True)
class Factor:
    factor_code: str
    points: int
    is_critical_block: bool
    detail: str
    evidence: dict | None = None

def factores_listas_sat(sat_hits: list[dict]) -> list[Factor]:
    if any(h.get("factor_code") == "rfc_formato_invalido" for h in sat_hits):
        return [Factor("rfc_formato_invalido", 60, False, "El RFC no pasa la validación de estructura — no se puede confiar en ninguna consulta SAT hecha con este dato.")]

    factores = []
    for hit in sat_hits:
        if hit["list_type"] == "art_69b" and hit["match_substate"] == "definitivo":
            factores.append(Factor("sat_69b_definitivo", 100, True, "RFC localizado en el listado definitivo de EFOS (Art. 69-B CFF)."))
        elif hit["list_type"] == "art_69b" and hit["match_substate"] == "presunto":
            factores.append(Factor("sat_69b_presunto", 40, False, "RFC localizado en el listado presunto de EFOS (Art. 69-B CFF)."))
        elif hit["list_type"] == "art_69b_bis":
            factores.append(Factor("sat_69b_bis", 35, False, "RFC en el listado de transmisión indebida de pérdidas fiscales (Art. 69-B Bis CFF)."))
        elif hit["list_type"] == "art_69":
            factores.append(Factor("sat_69_incumplido", 25, False, "RFC en el listado de contribuyentes incumplidos (Art. 69 CFF)."))

    factores.append(Factor("art_49bis_no_verificable", 0, False, "El Art. 49 Bis CFF no tiene lista pública consultable — requiere revisión manual.", evidence={"manual_review_required": True}))
    return factores

def factores_discrepancias(resultado) -> list[Factor]:
    factores = []
    if resultado.rfc_discrepante:
        factores.append(Factor("disc_rfc", 50, False, "El RFC no coincide entre los documentos del expediente."))
    if resultado.razon_social_discrepante:
        factores.append(Factor("disc_razon_social", 30, False, "La razón social no coincide de forma material entre los documentos."))
    if resultado.domicilio_discrepante:
        factores.append(Factor("disc_domicilio", 20, False, "El domicilio no coincide de forma material entre los documentos."))
    if resultado.representante_discrepante:
        factores.append(Factor("disc_representante", 25, False, "El nombre del representante legal no coincide entre los documentos."))
    if resultado.fechas_inconsistentes:
        factores.append(Factor("disc_fechas", 15, False, "Inconsistencia entre fechas de emisión/vigencia/vencimiento."))
    return factores

DOCUMENTOS_ESPERADOS = {
    "acta_constitutiva", "identificacion_rep_legal", "poder_notarial", "encargo_conferido",
    "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
}
VIGENCIA_DIAS = {"comprobante_domicilio": 90}

def factores_completitud(documentos: list[dict], socios: list[dict], hoy) -> list[Factor]:
    factores = []
    presentes = {d["doc_type"] for d in documentos}
    for esperado in DOCUMENTOS_ESPERADOS - presentes:
        factores.append(Factor("doc_missing", 15, False, f"Falta el documento: {esperado}.", evidence={"doc_type": esperado}))

    for doc in documentos:
        if doc["extraction_status"] != "human_reviewed":
            continue
        fields = doc.get("fields") or {}
        if any(v in (None, "") for v in fields.values()):
            factores.append(Factor("doc_data_incomplete", 15, False, f"El documento {doc['doc_type']} no aportó todos los campos obligatorios.", evidence={"documento_id": doc["id"]}))
        if doc["doc_type"] == "comprobante_domicilio" and doc.get("fecha_emision"):
            dias = (hoy - doc["fecha_emision"]).days
            if dias > VIGENCIA_DIAS["comprobante_domicilio"]:
                factores.append(Factor("doc_expired", 20, False, f"Comprobante de domicilio con {dias} días de antigüedad."))
        if doc["doc_type"] == "csf" and doc.get("fecha_emision"):
            if (doc["fecha_emision"].year, doc["fecha_emision"].month) != (hoy.year, hoy.month):
                factores.append(Factor("csf_stale", 25, False, "La CSF no corresponde al mes calendario vigente."))
        if doc["doc_type"] == "manifestacion_protesta" and not fields.get("declara_no_69b_49bis"):
            factores.append(Factor("manifestacion_incompleta", 20, False, "La Manifestación bajo Protesta no confirma la cláusula de los Art. 69-B / 49 Bis CFF."))

    acta = next((d for d in documentos if d["doc_type"] == "acta_constitutiva"), None)
    if acta and not socios:
        factores.append(Factor("socios_incompletos", 20, False, "El acta constitutiva está presente pero no se registraron socios/accionistas/beneficiario controlador."))

    rep_legal_doc = next((d for d in documentos if d["doc_type"] == "identificacion_rep_legal"), None)
    if rep_legal_doc and not (rep_legal_doc.get("fields") or {}).get("nombre_completo"):
        factores.append(Factor("rep_legal_incompleto", 15, False, "No se capturó el nombre completo del representante legal."))
    return factores
