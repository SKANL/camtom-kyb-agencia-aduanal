from pathlib import Path
import sys

# pytest adds backend/src/ to sys.path[0], but the src.* imports in main.py
# and admin.py need backend/ in the path for the namespace package resolution.
# This is the same resolution that happens in Vercel (root = backend/).
_backend_root = str(Path(__file__).resolve().parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.api.deps import get_supabase_client


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
