from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.deps import get_supabase_client
from api.routers.documentos import router


_EXP_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4 test content"


@pytest.fixture
def mock_supabase():
    return MagicMock()


@pytest.fixture
def client(mock_supabase):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
    return TestClient(app)


def test_upload_creates_documento(client, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "doc-123"}]
    mock_supabase.storage.from_.return_value.upload.return_value = {"path": f"{_EXP_ID}/csf.pdf"}

    with patch("api.routers.documentos.extraer_texto_de_bytes", return_value="RFC: EKU9003173C9"):
        with patch("api.routers.documentos.extraer_campos", return_value={"rfc": "EKU9003173C9"}):
            resp = client.post(
                "/documentos/upload",
                data={"expediente_id": _EXP_ID, "doc_type": "csf"},
                files={"file": ("csf.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert "documento_id" in body
    assert body["doc_type"] == "csf"
    assert body["extraction_status"] == "extracted"


def test_upload_returns_409_on_duplicate(client, mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": "existing-doc-id"}
    ]

    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": _EXP_ID, "doc_type": "csf"},
        files={"file": ("csf.pdf", _make_pdf_bytes(), "application/pdf")},
    )

    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["documento_id"] == "existing-doc-id"


def test_upload_rejects_invalid_doc_type(client, mock_supabase):
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": _EXP_ID, "doc_type": "invalid_type"},
        files={"file": ("x.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == 422


def test_upload_rejects_path_traversal_in_expediente_id(client, mock_supabase):
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": "../../etc/passwd", "doc_type": "csf"},
        files={"file": ("x.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == 422
