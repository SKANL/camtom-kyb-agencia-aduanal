import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.deps import get_supabase_client
from api.routers.expedientes import router


@pytest.fixture
def app(fake_supabase):
    _app = FastAPI()
    _app.include_router(router, prefix="/expedientes")
    _app.dependency_overrides[get_supabase_client] = lambda: fake_supabase
    return _app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /expedientes
# ---------------------------------------------------------------------------

def test_list_expedientes_returns_empty_list(client, fake_supabase):
    response = client.get("/expedientes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_expedientes_returns_existing_records(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "exp-1", "razon_social": "Empresa A", "rfc": "EMP123456789", "status": "pending"},
        {"id": "exp-2", "razon_social": "Empresa B", "rfc": "EMP987654321", "status": "safe"},
    ]
    response = client.get("/expedientes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


# ---------------------------------------------------------------------------
# POST /expedientes
# ---------------------------------------------------------------------------

def test_crear_expediente_inserts_row_and_returns_it(client, fake_supabase):
    response = client.post(
        "/expedientes",
        json={"razon_social": "Nueva Empresa SA", "rfc": "nue010101abc"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["razon_social"] == "Nueva Empresa SA"
    assert data["rfc"] == "NUE010101ABC"  # uppercased
    assert data["status"] == "pending"
    assert data["decision"] is None
    assert data["score_total"] is None
    rows = fake_supabase.store.get("expedientes", [])
    assert len(rows) == 1
    assert rows[0]["rfc"] == "NUE010101ABC"


def test_crear_expediente_with_optional_fields(client, fake_supabase):
    response = client.post(
        "/expedientes",
        json={
            "razon_social": "Empresa Completa SA",
            "rfc": "ECO010101XYZ",
            "domicilio_fiscal": "Av. Reforma 1, CDMX",
            "representante_legal": "Juan Perez",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["domicilio_fiscal"] == "Av. Reforma 1, CDMX"
    assert data["representante_legal"] == "Juan Perez"


# ---------------------------------------------------------------------------
# GET /expedientes/{id}
# ---------------------------------------------------------------------------

def test_get_expediente_returns_200_for_known_id(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "exp-abc", "razon_social": "Test SA", "rfc": "TST123456789", "status": "pending"}
    ]
    response = client.get("/expedientes/exp-abc")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "exp-abc"
    assert data["razon_social"] == "Test SA"


def test_get_expediente_returns_404_for_unknown_id(client, fake_supabase):
    response = client.get("/expedientes/no-existe")
    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /expedientes/{id}/evaluations/latest
# ---------------------------------------------------------------------------

def test_get_latest_evaluation_returns_none_when_no_evaluations(client, fake_supabase):
    response = client.get("/expedientes/exp-1/evaluations/latest")
    assert response.status_code == 200
    assert response.json() is None


def test_get_latest_evaluation_returns_shaped_evaluation(client, fake_supabase):
    fake_supabase.store["evaluations"] = [
        {
            "id": "eval-1",
            "expediente_id": "exp-1",
            "decision": "safe",
            "score_total": 80,
            "critical_blocks": ["F_SAT_ART69"],
            "summary": {
                "acciones_sugeridas": ["Verificar domicilio fiscal"],
                "factores_score": {"F_SAT_ART69": -100},
                "factores_detail": [
                    {
                        "factor_code": "F_SAT_ART69",
                        "points": -100,
                        "is_critical_block": True,
                        "detail": "RFC en lista Art. 69",
                        "evidence": {},
                        "legal_ref": "",
                        "category": "sat",
                    }
                ],
            },
            "created_at": "2026-06-28T10:00:00Z",
        }
    ]
    response = client.get("/expedientes/exp-1/evaluations/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "safe"
    assert data["score_total"] == 80
    assert "F_SAT_ART69" in data["factores_score"]
    assert data["factores_detail"][0]["factor_code"] == "F_SAT_ART69"
    assert data["acciones_sugeridas"] == ["Verificar domicilio fiscal"]
    assert data["evaluated_at"] == "2026-06-28T10:00:00Z"


# ---------------------------------------------------------------------------
# GET /expedientes/{id}/consultas-sat
# ---------------------------------------------------------------------------

def test_get_consultas_sat_returns_empty_list(client, fake_supabase):
    response = client.get("/expedientes/exp-1/consultas-sat")
    assert response.status_code == 200
    assert response.json() == []


def test_get_consultas_sat_returns_records_for_expediente(client, fake_supabase):
    fake_supabase.store["consultas_sat"] = [
        {"id": "c-1", "expediente_id": "exp-1", "list_type": "art_69", "rfc": "TST123", "resultado": "not_found"},
        {"id": "c-2", "expediente_id": "exp-2", "list_type": "art_69b", "rfc": "OTR456", "resultado": "found"},
    ]
    response = client.get("/expedientes/exp-1/consultas-sat")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "c-1"


def test_get_consultas_sat_uses_consulted_at(client, fake_supabase):
    """Verify the query orders by consulted_at (not created_at which does not exist)."""
    # Set up a mock query object to track order calls
    from unittest.mock import MagicMock
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value.data = []

    # Replace the table method to return our mock
    original_table = fake_supabase.table
    fake_supabase.table = MagicMock(return_value=mock_query)

    try:
        response = client.get("/expedientes/exp-1/consultas-sat")
        assert response.status_code == 200
        # Verify the column used in order()
        mock_query.order.assert_called_once_with("consulted_at", desc=True)
    finally:
        fake_supabase.table = original_table


# ---------------------------------------------------------------------------
# PATCH /expedientes/{id}
# ---------------------------------------------------------------------------

def test_patch_expediente_updates_razon_social(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "abc-123", "razon_social": "Original SA", "rfc": "ORI010101AB1",
         "domicilio_fiscal": "", "representante_legal": "", "status": "pending",
         "decision": None, "score_total": None}
    ]
    response = client.patch("/expedientes/abc-123", json={"razon_social": "Nueva SA"})
    assert response.status_code == 200
    data = response.json()
    assert data["razon_social"] == "Nueva SA"


def test_patch_expediente_uppercases_rfc(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "abc-123", "razon_social": "X", "rfc": "OLD010101AB1",
         "domicilio_fiscal": "", "representante_legal": "", "status": "pending",
         "decision": None, "score_total": None}
    ]
    response = client.patch("/expedientes/abc-123", json={"rfc": "new010101ab1"})
    assert response.status_code == 200
    assert response.json()["rfc"] == "NEW010101AB1"


def test_patch_expediente_returns_404_for_unknown_id(client, fake_supabase):
    response = client.patch("/expedientes/no-such-id", json={"razon_social": "X"})
    assert response.status_code == 404


def test_patch_expediente_rejects_empty_body(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "abc-123", "razon_social": "X", "rfc": "ABC010101AB1",
         "domicilio_fiscal": "", "representante_legal": "", "status": "pending",
         "decision": None, "score_total": None}
    ]
    response = client.patch("/expedientes/abc-123", json={})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /expedientes/{id}
# ---------------------------------------------------------------------------

def test_delete_expediente_returns_204(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "del-123", "razon_social": "X", "rfc": "DEL010101AB1",
         "domicilio_fiscal": "", "representante_legal": "", "status": "pending",
         "decision": None, "score_total": None}
    ]
    response = client.delete("/expedientes/del-123")
    assert response.status_code == 204


def test_delete_expediente_returns_404_for_unknown_id(client, fake_supabase):
    response = client.delete("/expedientes/no-such-id")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /expedientes/{id}/evaluations
# ---------------------------------------------------------------------------

def test_list_evaluations_returns_history(client, fake_supabase):
    """GET /expedientes/{id}/evaluations returns list of past evaluations (most recent first)."""
    expediente_id = "exp-hist-1"
    # Seed in descending order so insertion-order matches expected sort (fake does not sort)
    fake_supabase.store["evaluations"] = [
        {"id": "ev-2", "expediente_id": expediente_id, "score_total": 0,
         "decision": "safe", "critical_blocks": [], "summary": {},
         "created_at": "2026-06-29T10:00:00Z"},
        {"id": "ev-1", "expediente_id": expediente_id, "score_total": 50,
         "decision": "review_required", "critical_blocks": [], "summary": {},
         "created_at": "2026-06-28T10:00:00Z"},
    ]
    resp = client.get(f"/expedientes/{expediente_id}/evaluations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["decision"] == "safe"           # most recent first
    assert data[1]["decision"] == "review_required"
