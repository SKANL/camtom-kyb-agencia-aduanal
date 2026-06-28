from fastapi import APIRouter, UploadFile

router = APIRouter()


@router.post("/admin/ocr-spike")
async def ocr_spike(file: UploadFile):
    from src.infrastructure.ai.ocr import ocr_imagen
    from PIL import Image
    import io

    image = Image.open(io.BytesIO(await file.read()))
    texto = ocr_imagen(image)
    return {"texto_extraido": texto[:500], "largo": len(texto)}
