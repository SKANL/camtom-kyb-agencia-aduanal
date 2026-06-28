from unittest.mock import patch, MagicMock
from infrastructure.ai.pdf import extraer_texto

def test_extraer_texto_usa_capa_nativa_si_hay_suficiente_texto():
    with patch("infrastructure.ai.pdf.PdfReader") as mock_reader:
        pagina = MagicMock(); pagina.extract_text.return_value = "Constancia de Situación Fiscal " * 5
        mock_reader.return_value.pages = [pagina]
        assert "Constancia" in extraer_texto("fake.pdf")

def test_extraer_texto_cae_a_ocr_si_no_hay_capa_de_texto():
    with patch("infrastructure.ai.pdf.PdfReader") as mock_reader, \
         patch("infrastructure.ai.pdf.convert_from_path") as mock_convert, \
         patch("infrastructure.ai.pdf.ocr_imagen", return_value="texto via ocr"):
        pagina = MagicMock(); pagina.extract_text.return_value = ""
        mock_reader.return_value.pages = [pagina]
        mock_convert.return_value = [MagicMock()]
        assert extraer_texto("fake_escaneado.pdf") == "texto via ocr"
