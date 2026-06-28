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
