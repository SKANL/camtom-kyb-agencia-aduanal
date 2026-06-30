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
        patch("api.routers.documentos.extraer_texto_de_bytes") as mock_texto,
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
        json={"fields": {"rfc": "ABC123456789", "razon_social": "Mi Empresa SA"}},
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


# ---------------------------------------------------------------------------
# GET /documentos?expediente_id=...
# ---------------------------------------------------------------------------

def test_list_documentos_returns_200_with_list(client, fake_supabase):
    fake_supabase.store["documentos"] = [
        {"id": "doc-1", "expediente_id": "exp-1", "doc_type": "csf", "entry_method": "manual"},
        {"id": "doc-2", "expediente_id": "exp-1", "doc_type": "acta_constitutiva", "entry_method": "manual"},
    ]
    response = client.get("/documentos?expediente_id=exp-1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_documentos_filters_by_expediente_id(client, fake_supabase):
    fake_supabase.store["documentos"] = [
        {"id": "doc-1", "expediente_id": "exp-1", "doc_type": "csf", "entry_method": "manual"},
        {"id": "doc-2", "expediente_id": "exp-2", "doc_type": "acta_constitutiva", "entry_method": "uploaded"},
    ]
    response = client.get("/documentos?expediente_id=exp-1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "doc-1"
    assert data[0]["expediente_id"] == "exp-1"


def test_list_documentos_returns_empty_list_when_no_match(client, fake_supabase):
    fake_supabase.store["documentos"] = [
        {"id": "doc-1", "expediente_id": "exp-other", "doc_type": "csf", "entry_method": "manual"},
    ]
    response = client.get("/documentos?expediente_id=exp-1")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Task 4: upload extraction failure → needs_review (option B)
# ---------------------------------------------------------------------------

_VALID_EXP_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


def test_upload_rfc_doc_type_succeeds(client, fake_supabase):
    """rfc is now a valid doc_type — upload should not 422."""
    import io
    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": _VALID_EXP_ID, "doc_type": "rfc"},
        files={"file": ("rfc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "documento_id" in body
    assert "needs_review" in body


def test_upload_extraction_failure_returns_pending_with_needs_review(client, fake_supabase, monkeypatch):
    """When extraer_campos raises, upload returns 200 with needs_review=True."""
    import io
    from api.routers import documentos as doc_router

    def failing_extractor(*args, **kwargs):
        raise RuntimeError("Groq unavailable")

    monkeypatch.setattr(doc_router, "extraer_campos", failing_extractor)
    monkeypatch.setattr(doc_router, "extraer_texto_de_bytes", lambda b: "Texto no vacio")

    pdf_bytes = b"%PDF-1.4\n%%EOF"
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": _VALID_EXP_ID, "doc_type": "csf"},
        files={"file": ("csf.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["extraction_status"] == "pending"
    assert body["needs_review"] is True


def test_upload_success_returns_needs_review_false(client, fake_supabase, monkeypatch):
    """Successful extraction returns needs_review=False."""
    import io
    from api.routers import documentos as doc_router

    def mock_extractor(supabase, doc_type, texto):
        return {"rfc": "EKU9003173C9", "razon_social": "Test SA de CV"}

    monkeypatch.setattr(doc_router, "extraer_campos", mock_extractor)
    monkeypatch.setattr(doc_router, "extraer_texto_de_bytes", lambda b: "RFC: EKU9003173C9")

    pdf_bytes = b"%PDF-1.4\n%%EOF"
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": _VALID_EXP_ID, "doc_type": "csf"},
        files={"file": ("csf.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is False
    assert body["extraction_status"] == "extracted"


# ---------------------------------------------------------------------------
# Task 5: extract_documento uses Storage bytes, not local path
# ---------------------------------------------------------------------------

def test_extract_documento_uses_storage_not_local_path(client, fake_supabase, monkeypatch):
    """extract_documento must download from Storage, not try to open a local file."""
    from api.routers import documentos as doc_router

    downloaded = []

    original_from = fake_supabase.storage.from_

    def patched_from(bucket_name):
        bucket = original_from(bucket_name)
        original_download = bucket.download

        def tracking_download(path):
            downloaded.append(path)
            return original_download(path)

        bucket.download = tracking_download
        return bucket

    fake_supabase.storage.from_ = patched_from

    monkeypatch.setattr(doc_router, "extraer_texto_de_bytes", lambda b: "RFC: EKU9003173C9")
    monkeypatch.setattr(doc_router, "extraer_campos", lambda *a, **kw: {"rfc": "EKU9003173C9"})

    doc_id = "test-doc-id-extract"
    fake_supabase.table("documentos").insert({
        "id": doc_id, "expediente_id": "exp-1", "doc_type": "csf",
        "storage_path": "exp-1/csf.pdf", "extraction_status": "pending",
        "entry_method": "uploaded", "fields": {},
    }).execute()

    resp = client.post(f"/documentos/{doc_id}/extract")
    assert resp.status_code == 200
    assert len(downloaded) == 1, "Storage download should have been called"
    assert downloaded[0] == "exp-1/csf.pdf"


# ---------------------------------------------------------------------------
# Task 6: DELETE /documentos/{id}
# ---------------------------------------------------------------------------

def test_delete_documento_returns_204(client, fake_supabase):
    """DELETE /documentos/{id} removes the doc record and returns 204."""
    doc_id = "doc-to-delete"
    fake_supabase.table("documentos").insert({
        "id": doc_id, "expediente_id": "exp-del", "doc_type": "rfc",
        "storage_path": "exp-del/rfc.pdf", "extraction_status": "pending",
        "entry_method": "uploaded", "fields": {},
    }).execute()

    resp = client.delete(f"/documentos/{doc_id}")
    assert resp.status_code == 204

    rows = fake_supabase.table("documentos").select("id").eq("id", doc_id).execute().data
    assert rows == []


def test_delete_documento_404_if_not_found(client, fake_supabase):
    resp = client.delete("/documentos/nonexistent-id")
    assert resp.status_code == 404
