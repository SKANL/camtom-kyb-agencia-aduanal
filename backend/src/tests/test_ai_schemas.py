import pytest
from pydantic import ValidationError
from infrastructure.ai.schemas import SCHEMA_REGISTRY, SimilarityResult


def test_csf_schema_acepta_campos_nulos():
    assert SCHEMA_REGISTRY["csf"](rfc=None, razon_social="X SA de CV").rfc is None


def test_similarity_result_rechaza_fuera_de_rango():
    with pytest.raises(ValidationError):
        SimilarityResult(similarity=1.5, same_entity=True, reasoning="x")


def test_encargo_conferido_tiene_su_propio_schema():
    schema = SCHEMA_REGISTRY["encargo_conferido"](
        rfc_agente_aduanal="ABC010101XX1", alcance="general", fecha_vigencia="2026-01-01"
    )
    assert schema.rfc_agente_aduanal == "ABC010101XX1"
