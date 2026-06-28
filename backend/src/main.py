from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import admin

app = FastAPI(title="Camtom KYB API")
app.include_router(admin.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO en Fase 5: restringir al dominio real del frontend en Vercel
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
