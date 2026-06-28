from PIL import Image


def ocr_imagen(imagen: Image.Image) -> str:
    """Extrae texto de una imagen usando Tesseract OCR (si está disponible).

    En Vercel serverless Tesseract NO está disponible (TesseractNotFoundError
    confirmado en spike de Fase 2). Esta función solo funciona en desarrollo
    local donde el binario 'tesseract' esté instalado.

    Para producción en Vercel, los PDFs deben tener capa de texto seleccionable
    y extraerse con PyMuPDF/pdfplumber (sin OCR). Ver "Riesgos documentados"
    en el plan de implementación.
    """
    try:
        import pytesseract
    except ImportError:
        raise RuntimeError(
            "pytesseract no está instalado. "
            "Instalación local: pip install pytesseract. "
            "En Vercel serverless Tesseract no está disponible."
        )
    return pytesseract.image_to_string(imagen, lang="spa")
