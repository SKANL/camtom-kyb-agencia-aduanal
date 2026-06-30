from dataclasses import dataclass, field

UMBRALES = {"razon_social": 0.85, "domicilio": 0.75, "representante_legal": 0.90}

@dataclass(frozen=True)
class ResultadoConciliacion:
    rfc_discrepante: bool
    razon_social_discrepante: bool
    domicilio_discrepante: bool
    representante_discrepante: bool
    fechas_inconsistentes: bool
    compared_values: dict = field(default_factory=dict)

def reconciliar(rfcs, similarity_razon_social, similarity_domicilio, similarity_representante, fechas_validas, compared_values=None) -> ResultadoConciliacion:
    rfcs_norm = {r.strip().upper() for r in rfcs if r}
    return ResultadoConciliacion(
        rfc_discrepante=len(rfcs_norm) > 1,
        razon_social_discrepante=(not similarity_razon_social["same_entity"]) and similarity_razon_social["similarity"] < UMBRALES["razon_social"],
        domicilio_discrepante=(not similarity_domicilio["same_entity"]) and similarity_domicilio["similarity"] < UMBRALES["domicilio"],
        representante_discrepante=(not similarity_representante["same_entity"]) and similarity_representante["similarity"] < UMBRALES["representante_legal"],
        fechas_inconsistentes=not fechas_validas,
        compared_values=compared_values or {},
    )
