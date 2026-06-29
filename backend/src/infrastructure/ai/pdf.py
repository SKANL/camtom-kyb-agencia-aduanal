import io

from pypdf import PdfReader
from pdf2image import convert_from_path
from infrastructure.ai.ocr import ocr_imagen

UMBRAL_TEXTO_MINIMO = 20

def extraer_texto(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    texto = "\n".join(page.extract_text() or "" for page in reader.pages)
    if len(texto.strip()) >= UMBRAL_TEXTO_MINIMO:
        return texto
    paginas = convert_from_path(pdf_path)
    return "\n".join(ocr_imagen(p) for p in paginas)


def extraer_texto_de_bytes(content: bytes) -> str:
    """Extract selectable text from PDF bytes without touching storage."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""
