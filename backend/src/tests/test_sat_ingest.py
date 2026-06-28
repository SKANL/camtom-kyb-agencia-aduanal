import pandas as pd
import pytest
from src.infrastructure.sat.ingest import ingest_list


@pytest.fixture
def art_69b_xlsx(tmp_path):
    df = pd.DataFrame({
        "RFC": ["ghi030303xx3"],
        "Nombre del Contribuyente": ["Empresa Fantasma SA de CV"],
        "Situación del Contribuyente": ["Definitivo"],
    })
    path = tmp_path / "art69b.xlsx"
    df.to_excel(path, index=False)
    return str(path)


@pytest.fixture
def art_69b_xlsx_vacio(tmp_path):
    df = pd.DataFrame({
        "RFC": [""],
        "Nombre del Contribuyente": ["Empresa Sin RFC SA de CV"],
        "Situación del Contribuyente": ["Definitivo"],
    })
    path = tmp_path / "art69b_vacio.xlsx"
    df.to_excel(path, index=False)
    return str(path)


def test_ingest_list_carga_registros_y_cierra_el_run(fake_supabase, art_69b_xlsx):
    result = ingest_list(fake_supabase, "art_69b", art_69b_xlsx)
    assert result["rows_imported"] == 1
    assert fake_supabase.store["sat_lista_registros"][0]["rfc"] == "GHI030303XX3"
    assert fake_supabase.store["sat_import_runs"][0]["status"] == "success"


def test_ingest_list_borra_registros_previos_del_mismo_list_type(fake_supabase, art_69b_xlsx):
    # import_batch_id es NOT NULL en el schema real (toda fila de una corrida
    # previa real tiene un UUID propio, nunca None) — el fixture debe reflejar
    # eso para no ocultar el comportamiento NULL-aware de Supabase/PostgREST.
    fake_supabase.store["sat_lista_registros"] = [
        {"list_type": "art_69b", "rfc": "VIEJO000000X00", "import_batch_id": "batch-anterior"}
    ]
    ingest_list(fake_supabase, "art_69b", art_69b_xlsx)
    assert "VIEJO000000X00" not in [r["rfc"] for r in fake_supabase.store["sat_lista_registros"]]


def test_ingest_list_lanza_error_claro_para_list_type_desconocido(fake_supabase, art_69b_xlsx):
    with pytest.raises(ValueError, match="list_type desconocido"):
        ingest_list(fake_supabase, "art_70_inexistente", art_69b_xlsx)


def test_ingest_list_lanza_error_claro_si_no_hay_parser_para_list_type_con_source(fake_supabase, art_69b_xlsx):
    with pytest.raises(ValueError, match="no hay parser implementado"):
        ingest_list(fake_supabase, "art_69b_bis", art_69b_xlsx)


def test_ingest_list_marca_run_failed_y_preserva_registros_viejos_si_falla_insert(fake_supabase, art_69b_xlsx):
    fake_supabase.store["sat_lista_registros"] = [{"list_type": "art_69b", "rfc": "VIEJO000000X00"}]
    fake_supabase.fail_on_insert["sat_lista_registros"] = RuntimeError("timeout simulado de Supabase")

    with pytest.raises(RuntimeError, match="timeout simulado"):
        ingest_list(fake_supabase, "art_69b", art_69b_xlsx)

    run = fake_supabase.store["sat_import_runs"][0]
    assert run["status"] == "failed"
    assert run["finished_at"] is not None

    registros_viejos = fake_supabase.store["sat_lista_registros"]
    assert len(registros_viejos) == 1
    assert registros_viejos[0]["rfc"] == "VIEJO000000X00"


def test_ingest_list_xlsx_inexistente_no_crea_run(fake_supabase):
    with pytest.raises(FileNotFoundError):
        ingest_list(fake_supabase, "art_69b", "/ruta/que/no/existe.xlsx")

    assert fake_supabase.store.get("sat_import_runs", []) == []


def test_ingest_list_con_registros_vacios_completa_sin_error(fake_supabase, art_69b_xlsx_vacio):
    result = ingest_list(fake_supabase, "art_69b", art_69b_xlsx_vacio)

    assert result["rows_imported"] == 0
    assert fake_supabase.store["sat_import_runs"][0]["status"] == "success"
    assert fake_supabase.store.get("sat_lista_registros", []) == []
