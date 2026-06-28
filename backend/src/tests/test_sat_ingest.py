import pandas as pd
import pytest
from infrastructure.sat.ingest import ingest_list


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


def test_ingest_list_carga_registros_y_cierra_el_run(fake_supabase, art_69b_xlsx):
    result = ingest_list(fake_supabase, "art_69b", art_69b_xlsx)
    assert result["rows_imported"] == 1
    assert fake_supabase.store["sat_lista_registros"][0]["rfc"] == "GHI030303XX3"
    assert fake_supabase.store["sat_import_runs"][0]["status"] == "success"


def test_ingest_list_borra_registros_previos_del_mismo_list_type(fake_supabase, art_69b_xlsx):
    fake_supabase.store["sat_lista_registros"] = [{"list_type": "art_69b", "rfc": "VIEJO000000X00"}]
    ingest_list(fake_supabase, "art_69b", art_69b_xlsx)
    assert "VIEJO000000X00" not in [r["rfc"] for r in fake_supabase.store["sat_lista_registros"]]


def test_ingest_list_lanza_error_claro_para_list_type_desconocido(fake_supabase, art_69b_xlsx):
    with pytest.raises(ValueError, match="list_type desconocido"):
        ingest_list(fake_supabase, "art_70_inexistente", art_69b_xlsx)


def test_ingest_list_lanza_error_claro_si_no_hay_parser_para_list_type_con_source(fake_supabase, art_69b_xlsx):
    with pytest.raises(ValueError, match="no hay parser implementado"):
        ingest_list(fake_supabase, "art_69b_bis", art_69b_xlsx)
