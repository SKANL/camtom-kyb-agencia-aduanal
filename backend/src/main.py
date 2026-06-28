from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import admin
from src.api.routers.expedientes import router as expedientes_router

app = FastAPI(title="Camtom KYB API")
app.include_router(admin.router)
app.include_router(expedientes_router, prefix="/expedientes", tags=["expedientes"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO en Fase 5: restringir al dominio real del frontend en Vercel
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
