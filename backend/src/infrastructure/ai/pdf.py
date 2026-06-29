import io

import pdfplumber
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


_MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_PDF_PAGES = 50


def extraer_texto_de_bytes(content: bytes) -> str:
    """Extract selectable text from PDF bytes without touching storage."""
    if len(content) > _MAX_PDF_BYTES:
        return ""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = pdf.pages[:_MAX_PDF_PAGES]
            return "\n".join(page.extract_text() or "" for page in pages)
    except Exception:
        return ""
