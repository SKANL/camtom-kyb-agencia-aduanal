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


def test_rfc_in_schema_registry():
    from infrastructure.ai.schemas import SCHEMA_REGISTRY
    assert "rfc" in SCHEMA_REGISTRY


def test_rfc_fields_structure():
    from infrastructure.ai.schemas import SCHEMA_REGISTRY, RfcFields
    schema = SCHEMA_REGISTRY["rfc"]
    assert schema is RfcFields
    instance = RfcFields(rfc="EKU9003173C9", razon_social="Test SA de CV", domicilio_fiscal="Calle 1")
    assert instance.rfc == "EKU9003173C9"
    assert instance.razon_social == "Test SA de CV"
    assert instance.domicilio_fiscal == "Calle 1"


def test_rfc_fields_all_optional():
    from infrastructure.ai.schemas import RfcFields
    instance = RfcFields()
    assert instance.rfc is None
    assert instance.razon_social is None
    assert instance.domicilio_fiscal is None


def test_manifestacion_schema_default_is_none():
    """declara_no_69b_49bis must default to None so absent != explicit negative."""
    from infrastructure.ai.schemas import ManifestacionProtestaFields
    m = ManifestacionProtestaFields()
    assert m.declara_no_69b_49bis is None, (
        f"Default should be None (not False) — got {m.declara_no_69b_49bis!r}. "
        "A False default means an absent field is indistinguishable from explicit negation."
    )
