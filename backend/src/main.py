from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Camtom KYB API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO en Fase 5: restringir al dominio real del frontend en Vercel
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
