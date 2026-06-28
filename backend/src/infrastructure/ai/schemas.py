from pydantic import BaseModel, Field


class CsfFields(BaseModel):
    rfc: str | None = None
    razon_social: str | None = None
    domicilio_fiscal: str | None = None
    fecha_emision: str | None = None
    regimen_fiscal: str | None = None


class ActaConstitutivaFields(BaseModel):
    rfc: str | None = None
    razon_social: str | None = None
    socios: list[dict] = Field(default_factory=list)


class ComprobanteDomicilioFields(BaseModel):
    domicilio: str | None = None
    fecha_emision: str | None = None


class IdentificacionRepLegalFields(BaseModel):
    nombre_completo: str | None = None
    fecha_vencimiento: str | None = None


class PoderNotarialFields(BaseModel):
    nombre_representante: str | None = None
    alcance: str | None = None


class EncargoConferidoFields(BaseModel):
    rfc_agente_aduanal: str | None = None
    alcance: str | None = None
    fecha_vigencia: str | None = None


class ManifestacionProtestaFields(BaseModel):
    declara_no_69b_49bis: bool = False


class SimilarityResult(BaseModel):
    similarity: float = Field(ge=0.0, le=1.0)
    same_entity: bool
    reasoning: str


SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "csf": CsfFields,
    "acta_constitutiva": ActaConstitutivaFields,
    "comprobante_domicilio": ComprobanteDomicilioFields,
    "identificacion_rep_legal": IdentificacionRepLegalFields,
    "poder_notarial": PoderNotarialFields,
    "encargo_conferido": EncargoConferidoFields,
    "manifestacion_protesta": ManifestacionProtestaFields,
}
