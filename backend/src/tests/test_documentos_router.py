from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.deps import get_supabase_client
from api.routers.documentos import router
from fastapi import FastAPI


@pytest.fixture
def app(fake_supabase):
    _app = FastAPI()
    _app.include_router(router)
    _app.dependency_overrides[get_supabase_client] = lambda: fake_supabase
    return _app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_crear_documento_manual(client, fake_supabase):
    response = client.post(
        "/documentos",
        json={"expediente_id": "exp-1", "doc_type": "acta_constitutiva", "entry_method": "manual"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "documento_id" in data
    assert "signed_url" not in data
    # Verify row was inserted
    rows = fake_supabase.store.get("documentos", [])
    assert len(rows) == 1
    assert rows[0]["extraction_status"] == "not_applicable"
    assert rows[0]["entry_method"] == "manual"


def test_crear_documento_uploaded_returns_signed_url(client, fake_supabase):
    with patch("api.routers.documentos.crear_signed_upload_url") as mock_url:
        mock_url.return_value = {"signed_url": "https://storage.example.com/upload", "token": "tok123"}
        response = client.post(
            "/documentos",
            json={"expediente_id": "exp-1", "doc_type": "csf", "entry_method": "uploaded"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "documento_id" in data
    assert data["signed_url"] == "https://storage.example.com/upload"
    assert data["token"] == "tok123"
    rows = fake_supabase.store.get("documentos", [])
    assert rows[0]["extraction_status"] == "pending"
    assert rows[0]["storage_path"] == "exp-1/csf.pdf"


def test_extract_documento(client, fake_supabase):
    doc_id = "doc-abc"
    fake_supabase.store["documentos"] = [
        {"id": doc_id, "expediente_id": "exp-1", "doc_type": "csf", "storage_path": "exp-1/csf.pdf"}
    ]
    with (
        patch("api.routers.documentos.extraer_texto") as mock_texto,
        patch("api.routers.documentos.extraer_campos") as mock_campos,
    ):
        mock_texto.return_value = "Texto del PDF"
        mock_campos.return_value = {"rfc": "EKU9003173C9", "razon_social": "Empresa SA"}
        response = client.post(f"/documentos/{doc_id}/extract")

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_status"] == "extracted"
    assert data["fields"]["rfc"] == "EKU9003173C9"


def test_extract_documento_404_si_no_existe(client, fake_supabase):
    response = client.post("/documentos/no-existe/extract")
    assert response.status_code == 404
    assert response.json()["detail"] == "Documento no encontrado"


def test_patch_documento_human_reviewed(client, fake_supabase):
    doc_id = "doc-xyz"
    fake_supabase.store["documentos"] = [
        {"id": doc_id, "expediente_id": "exp-1", "doc_type": "acta_constitutiva", "extraction_status": "not_applicable"}
    ]
    response = client.patch(
        f"/documentos/{doc_id}",
        json={"rfc": "ABC123456789", "razon_social": "Mi Empresa SA"},
    )
    assert response.status_code == 200
    assert response.json()["extraction_status"] == "human_reviewed"
    rows = fake_supabase.store.get("documentos", [])
    updated = next(r for r in rows if r["id"] == doc_id)
    assert updated["extraction_status"] == "human_reviewed"


def test_crear_documento_doc_type_invalido_retorna_422(client, fake_supabase):
    response = client.post(
        "/documentos",
        json={"expediente_id": "exp-1", "doc_type": "doc_falso", "entry_method": "manual"},
    )
    assert response.status_code == 422
    assert "doc_type inválido" in response.json()["detail"]
