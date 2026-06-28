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
