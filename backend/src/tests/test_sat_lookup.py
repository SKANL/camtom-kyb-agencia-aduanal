from infrastructure.sat.lookup import consultar_rfc_en_listas


def test_rfc_invalido_no_consulta_nada(fake_supabase):
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "ABC123")
    assert resultado == [{"factor_code": "rfc_formato_invalido", "rfc": "ABC123"}]
    assert "consultas_sat" not in fake_supabase.store


def test_rfc_limpio_no_genera_hits(fake_supabase):
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "EKU9003173C9")
    assert resultado == []
    assert len(fake_supabase.store["consultas_sat"]) == 2  # art_69 + art_69b consultados y logueados


def test_rfc_en_69b_definitivo_genera_hit(fake_supabase):
    # GHI030303XX1: igual que el ejemplo del brief (GHI030303XX3) pero con el
    # digito verificador real (modulo 11), no inventado. GHI030303XX3 no pasa
    # validar_estructura (mismo tipo de defecto ya detectado y corregido para
    # EKU9003173C9 en un commit previo de esta fase) y el lookup cortaria en
    # el branch de rfc_formato_invalido antes de llegar a consultar listas.
    fake_supabase.store["sat_lista_registros"] = [
        {"list_type": "art_69b", "rfc": "GHI030303XX1", "art69b_substate": "definitivo", "situacion": "definitivo"}
    ]
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "GHI030303XX1")
    assert {"list_type": "art_69b", "match_substate": "definitivo"} in resultado


def test_import_run_id_queda_seteado_con_run_success_previo(fake_supabase):
    # Dos runs para el mismo list_type: uno viejo y uno mas reciente, ambos
    # success. consultar_rfc_en_listas debe resolver el MAS RECIENTE.
    fake_supabase.store["sat_import_runs"] = [
        {"id": "run-viejo", "list_type": "art_69b", "status": "success", "started_at": "2026-01-01T00:00:00+00:00"},
        {"id": "run-nuevo", "list_type": "art_69b", "status": "success", "started_at": "2026-06-01T00:00:00+00:00"},
        {"id": "run-otra-lista", "list_type": "art_69", "status": "success", "started_at": "2026-06-20T00:00:00+00:00"},
    ]
    consultar_rfc_en_listas(fake_supabase, "exp-1", "EKU9003173C9")

    consultas = fake_supabase.store["consultas_sat"]
    consulta_69b = next(c for c in consultas if c["list_type"] == "art_69b")
    consulta_69 = next(c for c in consultas if c["list_type"] == "art_69")

    assert consulta_69b["import_run_id"] == "run-nuevo"
    assert consulta_69["import_run_id"] == "run-otra-lista"


def test_import_run_id_queda_none_si_no_hay_run_success(fake_supabase):
    # Nunca se corrio la ingesta para ningun list_type: no debe romper la
    # consulta, debe loguear found=False con import_run_id=None explicito.
    resultado = consultar_rfc_en_listas(fake_supabase, "exp-1", "EKU9003173C9")

    assert resultado == []
    consultas = fake_supabase.store["consultas_sat"]
    assert len(consultas) == 2
    assert all(c["import_run_id"] is None for c in consultas)
    assert all(c["found"] is False for c in consultas)
