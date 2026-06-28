import pytesseract
from PIL import Image


def ocr_imagen(imagen: Image.Image) -> str:
    return pytesseract.image_to_string(imagen, lang="spa")
