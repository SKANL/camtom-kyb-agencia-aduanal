"""Tests the revisar_documento endpoint stores fields flat, not double-nested."""
import pytest
from fastapi.testclient import TestClient
from main import app
from api.deps import get_supabase_client


class FakeSupabase:
    def __init__(self):
        self._update_payload = None

    def table(self, name):
        return self

    def select(self, *args):
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def delete(self):
        return self

    def insert(self, payload):
        return self

    def eq(self, *args):
        return self

    def execute(self):
        class R:
            data = [{"id": "test-doc-id"}]
        return R()


@pytest.fixture()
def fake_sb():
    return FakeSupabase()


@pytest.fixture()
def client(fake_sb):
    app.dependency_overrides[get_supabase_client] = lambda: fake_sb
    with TestClient(app) as c:
        yield c, fake_sb
    app.dependency_overrides.clear()


def test_revisar_documento_stores_fields_flat(client):
    """PATCH /documentos/{id} with {fields: {rfc: X}} must store {rfc: X}, not {fields: {rfc: X}}."""
    http_client, sb = client
    fields_payload = {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV"}

    resp = http_client.patch("/documentos/test-doc-id", json={"fields": fields_payload})

    assert resp.status_code == 200, resp.text
    stored = sb._update_payload
    assert stored is not None
    assert stored["fields"] == fields_payload, (
        f"Expected {fields_payload}, got {stored['fields']}. "
        "Double-nesting bug: the whole body was stored instead of body['fields']."
    )
    assert stored.get("extraction_status") == "human_reviewed"


def test_revisar_documento_missing_fields_key_returns_422(client):
    """Sending raw dict without wrapping in 'fields' must return 422."""
    http_client, _ = client
    resp = http_client.patch("/documentos/test-doc-id", json={"rfc": "EKU9003173C9"})
    assert resp.status_code == 422
