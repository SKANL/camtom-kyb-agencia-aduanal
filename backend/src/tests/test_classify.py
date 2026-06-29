from unittest.mock import patch, MagicMock
from infrastructure.ai.classify import clasificar_documento

VALID_DOC_TYPES = {
    "csf", "acta_constitutiva", "comprobante_domicilio",
    "identificacion_rep_legal", "poder_notarial",
    "encargo_conferido", "manifestacion_protesta",
}

def test_clasificar_documento_returns_valid_doc_type():
    texto = "Constancia de Situación Fiscal\nServicio de Administración Tributaria\nRFC: EKU9003173C9"
    mock_response = MagicMock()
    mock_response.content = '{"doc_type": "csf", "confidence": "high"}'
    with patch("infrastructure.ai.classify.get_groq_model") as mock_model_fn:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_model_fn.return_value = mock_llm
        result = clasificar_documento(texto)
    assert result["doc_type"] in VALID_DOC_TYPES
    assert result["confidence"] in ("high", "low")

def test_clasificar_documento_falls_back_on_bad_json():
    mock_response = MagicMock()
    mock_response.content = "not valid json at all"
    with patch("infrastructure.ai.classify.get_groq_model") as mock_model_fn:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_model_fn.return_value = mock_llm
        result = clasificar_documento("some text")
    assert result["doc_type"] == "unknown"
    assert result["confidence"] == "low"
