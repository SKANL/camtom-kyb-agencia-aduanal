from unittest.mock import patch
from infrastructure.ai.similarity import comparar_semanticamente


def test_comparar_semanticamente_cachea_por_harness(fake_supabase):
    with patch("infrastructure.ai.similarity.get_groq_model") as mock_model:
        mock_model.return_value.with_structured_output.return_value.invoke.return_value.model_dump.return_value = {
            "similarity": 0.92, "same_entity": True, "reasoning": "Misma entidad, distinta puntuación."
        }
        r1 = comparar_semanticamente(fake_supabase, "razón social", "Corporativo X SA de CV", "Corporativo X")
        r2 = comparar_semanticamente(fake_supabase, "razón social", "Corporativo X SA de CV", "Corporativo X")
        assert r1 == r2
        assert mock_model.call_count == 1
