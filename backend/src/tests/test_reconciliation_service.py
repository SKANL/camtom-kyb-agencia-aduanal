from unittest.mock import patch

from services.reconciliation_service import reconciliar_expediente


def test_reconciliar_expediente_arma_los_3_pares_y_aplica_umbral(fake_supabase):
    fake_supabase.store["expedientes"] = [
        {
            "id": "exp-1",
            "rfc": "EKU9003173C9",
            "razon_social": "Escuela Kemper Urgate SA de CV",
            "domicilio_fiscal": "Av X 123",
            "representante_legal": "Juan Pérez",
        }
    ]
    fake_supabase.store["documentos"] = [
        {
            "id": "doc-1",
            "expediente_id": "exp-1",
            "doc_type": "csf",
            "fields": {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV"},
        }
    ]

    with patch("infrastructure.ai.similarity.get_groq_model") as mock_model:
        mock_model.return_value.with_structured_output.return_value.invoke.return_value.model_dump.return_value = {
            "similarity": 1.0,
            "same_entity": True,
            "reasoning": "x",
        }
        resultado = reconciliar_expediente(fake_supabase, "exp-1")

    assert resultado.rfc_discrepante is False
    assert resultado.razon_social_discrepante is False


def test_reconciliar_expediente_detecta_rfc_discrepante(fake_supabase):
    fake_supabase.store["expedientes"] = [
        {
            "id": "exp-2",
            "rfc": "EKU9003173C9",
            "razon_social": "Empresa SA de CV",
            "domicilio_fiscal": "Calle 1",
            "representante_legal": "Ana López",
        }
    ]
    fake_supabase.store["documentos"] = [
        {
            "id": "doc-2",
            "expediente_id": "exp-2",
            "doc_type": "csf",
            "fields": {"rfc": "OTRO000000001", "razon_social": "Empresa SA de CV"},
        }
    ]

    with patch("infrastructure.ai.similarity.get_groq_model") as mock_model:
        mock_model.return_value.with_structured_output.return_value.invoke.return_value.model_dump.return_value = {
            "similarity": 1.0,
            "same_entity": True,
            "reasoning": "identical",
        }
        resultado = reconciliar_expediente(fake_supabase, "exp-2")

    assert resultado.rfc_discrepante is True


def test_reconciliar_incluye_compared_values_cuando_hay_discrepancias(fake_supabase):
    """compared_values must carry the actual strings that differed."""
    from services.reconciliation_service import reconciliar_expediente
    from unittest.mock import patch
    eid = fake_supabase.make_expediente_id()
    fake_supabase.store["expedientes"] = [{
        "id": eid,
        "rfc": "EKU9003173C9",
        "razon_social": "Empresa Original",
        "domicilio_fiscal": "Av. A",
        "representante_legal": "Rep A",
    }]
    fake_supabase.store["documentos"] = [
        {"id": "doc-csf", "expediente_id": eid, "doc_type": "csf", "extraction_status": "human_reviewed",
         "fields": {"rfc": "EKU9003173C9", "razon_social": "Empresa Diferente"}},
        {"id": "doc-poder", "expediente_id": eid, "doc_type": "poder_notarial", "extraction_status": "human_reviewed",
         "fields": {"nombre_representante": "Rep B"}},
    ]
    # Mock similarity to return "not same entity" so discrepancias fire
    def mock_sim(client, field, a, b):
        return {"similarity": 0.1, "same_entity": False, "reasoning": "mock"}
    with patch("services.reconciliation_service.comparar_semanticamente", mock_sim):
        resultado = reconciliar_expediente(fake_supabase, eid)
    assert resultado.razon_social_discrepante
    cv = resultado.compared_values
    assert "razon_social" in cv, f"expected razon_social in compared_values; got {cv}"
    assert cv["razon_social"]["expediente"] == "Empresa Original"
    assert cv["razon_social"]["documento"] == "Empresa Diferente"
    assert cv["razon_social"]["documento_id"] == "doc-csf"
    assert "representante" in cv
    assert cv["representante"]["expediente"] == "Rep A"
    assert cv["representante"]["documento"] == "Rep B"
    assert cv["representante"]["documento_id"] == "doc-poder"
