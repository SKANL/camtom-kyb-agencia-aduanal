"""TDD for POST /admin/demo/seed endpoint."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.deps import get_supabase_client
from src.api.routers.admin import router as admin_router


@pytest.fixture
def admin_app(fake_supabase):
    _app = FastAPI()
    _app.include_router(admin_router)
    _app.dependency_overrides[get_supabase_client] = lambda: fake_supabase
    return _app


@pytest.fixture
def client(admin_app):
    return TestClient(admin_app)


def test_demo_seed_creates_three_expedientes(client, fake_supabase):
    """POST /admin/demo/seed creates exactly 3 demo expedientes."""
    resp = client.post("/admin/demo/seed")
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "expediente_ids" in body
    assert len(body["expediente_ids"]) == 3
    assert "message" in body


def test_demo_seed_is_idempotent(client, fake_supabase):
    """Calling seed twice cleans and re-creates — same 3 RFCs."""
    client.post("/admin/demo/seed")
    resp2 = client.post("/admin/demo/seed")
    assert resp2.status_code == 200
    # Should still be exactly 3 (not 6)
    all_exp = fake_supabase.table("expedientes").select("rfc").execute().data
    demo_rfcs = {r["rfc"] for r in all_exp if r["rfc"] in ("EKU9003173C9", "COX010101AB1", "AAA120730823")}
    assert len(demo_rfcs) == 3


def test_demo_seed_returns_evaluations(client, fake_supabase, monkeypatch):
    """Each seeded expediente gets evaluated and returns decision."""
    from src.services import evaluation_service, reconciliation_service

    def fake_recon(supabase, exp_id):
        from types import SimpleNamespace
        return SimpleNamespace(
            rfc_discrepante=False, razon_social_discrepante=False,
            domicilio_discrepante=False, representante_discrepante=False,
            fechas_inconsistentes=False,
        )

    def fake_eval(supabase, exp_id, recon, hoy=None):
        return {"score_total": 0, "decision": "safe", "factores_score": {},
                "factores_detail": [], "acciones_sugeridas": [], "needs_update": False}

    monkeypatch.setattr(reconciliation_service, "reconciliar_expediente", fake_recon)
    monkeypatch.setattr(evaluation_service, "evaluar_expediente", fake_eval)

    resp = client.post("/admin/demo/seed")
    assert resp.status_code == 200
    body = resp.json()
    assert "evaluations" in body
    assert len(body["evaluations"]) == 3
