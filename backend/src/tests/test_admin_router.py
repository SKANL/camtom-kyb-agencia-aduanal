import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.main import app
from src.api.deps import get_supabase_client
from src.api.routers.admin import router as admin_router


# ---------------------------------------------------------------------------
# Isolated app fixture for new endpoints (no file upload required)
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_app(fake_supabase):
    _app = FastAPI()
    _app.include_router(admin_router)
    _app.dependency_overrides[get_supabase_client] = lambda: fake_supabase
    return _app


@pytest.fixture
def admin_client(admin_app):
    return TestClient(admin_app)


@pytest.fixture
def art_69b_xlsx_bytes(tmp_path):
    df = pd.DataFrame({
        "RFC": ["ghi030303xx3"],
        "Nombre del Contribuyente": ["Empresa Fantasma SA de CV"],
        "Situación del Contribuyente": ["Definitivo"],
    })
    path = tmp_path / "art69b.xlsx"
    df.to_excel(path, index=False)
    return path.read_bytes()


@pytest.fixture
def art_69_xlsx_bytes(tmp_path):
    df = pd.DataFrame({
        "RFC": ["AAA010101AAA"],
        "Situación del contribuyente": ["Incumplido"],
        "Fracción": ["I;II;III"],
    })
    path = tmp_path / "art69.xlsx"
    df.to_excel(path, index=False)
    return path.read_bytes()


def test_post_admin_sat_ingest_devuelve_filas_importadas(fake_supabase, art_69b_xlsx_bytes):
    app.dependency_overrides[get_supabase_client] = lambda: fake_supabase
    client = TestClient(app)
    response = client.post(
        "/admin/sat/ingest/art_69b",
        files={"file": ("art69b.xlsx", art_69b_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    assert response.json()["rows_imported"] == 1
    app.dependency_overrides.clear()


def test_post_admin_sat_ingest_art_69_devuelve_filas_importadas(fake_supabase, art_69_xlsx_bytes):
    app.dependency_overrides[get_supabase_client] = lambda: fake_supabase
    client = TestClient(app)
    response = client.post(
        "/admin/sat/ingest/art_69",
        files={"file": ("art69.xlsx", art_69_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    assert response.json()["rows_imported"] == 1
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /admin/sat-import-runs
# ---------------------------------------------------------------------------

def test_list_sat_import_runs_returns_200_with_list(admin_client, fake_supabase):
    fake_supabase.store["sat_import_runs"] = [
        {"id": "run-1", "list_type": "art_69", "status": "completed", "rows_imported": 10,
         "started_at": "2026-06-28T10:00:00Z", "finished_at": "2026-06-28T10:01:00Z"},
        {"id": "run-2", "list_type": "art_69b", "status": "completed", "rows_imported": 5,
         "started_at": "2026-06-28T09:00:00Z", "finished_at": "2026-06-28T09:01:00Z"},
    ]
    response = admin_client.get("/admin/sat-import-runs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_sat_import_runs_returns_empty_list_when_no_runs(admin_client, fake_supabase):
    response = admin_client.get("/admin/sat-import-runs")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /admin/ingest/{list_type}
# ---------------------------------------------------------------------------

def test_trigger_ingest_demo_returns_200_and_inserts_run(admin_client, fake_supabase):
    response = admin_client.post("/admin/ingest/art_69")
    assert response.status_code == 200
    data = response.json()
    assert data["list_type"] == "art_69"
    assert data["status"] == "completed"
    assert data["rows_imported"] == 0
    assert "id" in data
    assert "started_at" in data
    assert "finished_at" in data
    # Verify the run was persisted in the store
    runs = fake_supabase.store.get("sat_import_runs", [])
    assert len(runs) == 1
    assert runs[0]["list_type"] == "art_69"


def test_trigger_ingest_demo_different_list_types(admin_client, fake_supabase):
    for list_type in ["art_69", "art_69b", "art_69b_bis"]:
        fake_supabase.store.clear()
        response = admin_client.post(f"/admin/ingest/{list_type}")
        assert response.status_code == 200
        assert response.json()["list_type"] == list_type
        assert fake_supabase.store.get("sat_import_runs", [])[-1]["list_type"] == list_type
