from unittest.mock import patch

from infrastructure.ai.extract import extraer_campos


def test_extraer_campos_usa_el_harness_y_cachea(fake_supabase):
    with patch("infrastructure.ai.extract.get_groq_model") as mock_model:
        mock_model.return_value.with_structured_output.return_value.invoke.return_value.model_dump.return_value = {
            "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV"
        }
        r1 = extraer_campos(fake_supabase, "csf", "texto del documento")
        r2 = extraer_campos(fake_supabase, "csf", "texto del documento")
        assert r1 == r2
        assert mock_model.call_count == 1  # second call served from harness cache
