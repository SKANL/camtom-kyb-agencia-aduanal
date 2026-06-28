import pytest
from infrastructure.ai.harness import call_with_harness, compute_input_hash

def test_compute_input_hash_es_estable_para_el_mismo_payload():
    assert compute_input_hash("extraction", {"a": 1, "b": 2}) == compute_input_hash("extraction", {"b": 2, "a": 1})

def test_call_with_harness_cachea_y_no_vuelve_a_llamar(fake_supabase):
    llamadas = []
    def compute():
        llamadas.append(1)
        return {"similarity": 0.9}
    r1 = call_with_harness(fake_supabase, "similarity", {"a": "x"}, compute)
    r2 = call_with_harness(fake_supabase, "similarity", {"a": "x"}, compute)
    assert r1 == r2 == {"similarity": 0.9}
    assert len(llamadas) == 1

def test_call_with_harness_agota_reintentos_y_lanza(fake_supabase):
    def compute_que_siempre_falla():
        raise ValueError("parseo inválido")
    with pytest.raises(RuntimeError):
        call_with_harness(fake_supabase, "extraction", {"doc": "x"}, compute_que_siempre_falla, max_retries=2)
