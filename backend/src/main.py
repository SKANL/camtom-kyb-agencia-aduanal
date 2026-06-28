import os
import sys

# Add src/ to sys.path so imports work in Vercel runtime (/var/task/) and locally.
# Vercel loads src/main.py with /var/task/ as Python root, so 'from api.X' would
# fail without this. With src/ added, both Vercel and pytest share the same path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import admin
from api.routers.documentos import router as documentos_router
from api.routers.expedientes import router as expedientes_router

app = FastAPI(title="Camtom KYB API")
app.include_router(admin.router)
app.include_router(expedientes_router, prefix="/expedientes", tags=["expedientes"])
app.include_router(documentos_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO en Fase 5: restringir al dominio real del frontend en Vercel
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
