import pandas as pd
import pytest
from infrastructure.sat.parsers import parse_art_69, es_unicamente_fraccion_vi, parse_art_69b


@pytest.fixture
def art_69_xlsx(tmp_path):
    df = pd.DataFrame({
        "RFC": ["abc010101xx1", "DEF020202XX2"],
        "Situación del contribuyente": ["No localizado", "Crédito fiscal firme"],
        "Fracción": ["I", "VI"],
    })
    path = tmp_path / "art69.xlsx"
    df.to_excel(path, index=False)
    return str(path)


def test_parse_art_69_normaliza_rfc(art_69_xlsx):
    rows = parse_art_69(art_69_xlsx)
    assert rows[0]["rfc"] == "ABC010101XX1"


@pytest.fixture
def art_69_xlsx_con_fila_vacia(tmp_path):
    df = pd.DataFrame({
        "RFC": ["abc010101xx1", float("nan")],
        "Situación del contribuyente": ["No localizado", "Total: 1 registro"],
        "Fracción": ["I", float("nan")],
    })
    path = tmp_path / "art69_con_fila_vacia.xlsx"
    df.to_excel(path, index=False)
    return str(path)


def test_parse_art_69_descarta_fila_con_rfc_nan(art_69_xlsx_con_fila_vacia):
    rows = parse_art_69(art_69_xlsx_con_fila_vacia)
    assert len(rows) == 1
    assert rows[0]["rfc"] == "ABC010101XX1"


def test_es_unicamente_fraccion_vi_true():
    assert es_unicamente_fraccion_vi("VI") is True


def test_es_unicamente_fraccion_vi_true_con_minusculas():
    assert es_unicamente_fraccion_vi("vi") is True


def test_es_unicamente_fraccion_vi_false_con_otra_fraccion():
    assert es_unicamente_fraccion_vi("I; VI") is False


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


def test_parse_art_69b_mapea_substate_definitivo(art_69b_xlsx):
    rows = parse_art_69b(art_69b_xlsx)
    assert rows[0]["art69b_substate"] == "definitivo"


@pytest.fixture
def art_69b_xlsx_situacion_no_mapeada(tmp_path):
    df = pd.DataFrame({
        "RFC": ["jkl040404xx4"],
        "Nombre del Contribuyente": ["Empresa Desconocida SA de CV"],
        "Situación del Contribuyente": ["Situación no contemplada"],
    })
    path = tmp_path / "art69b_no_mapeado.xlsx"
    df.to_excel(path, index=False)
    return str(path)


def test_parse_art_69b_rechaza_situacion_no_mapeada(art_69b_xlsx_situacion_no_mapeada):
    with pytest.raises(ValueError, match="situacion no mapeada"):
        parse_art_69b(art_69b_xlsx_situacion_no_mapeada)


@pytest.fixture
def art_69b_xlsx_con_fila_vacia(tmp_path):
    df = pd.DataFrame({
        "RFC": ["mno050505xx5", float("nan")],
        "Nombre del Contribuyente": ["Empresa Real SA de CV", "Total: 1 registro"],
        "Situación del Contribuyente": ["Presunto", float("nan")],
    })
    path = tmp_path / "art69b_con_fila_vacia.xlsx"
    df.to_excel(path, index=False)
    return str(path)


def test_parse_art_69b_descarta_fila_vacia_sin_lanzar_error(art_69b_xlsx_con_fila_vacia):
    rows = parse_art_69b(art_69b_xlsx_con_fila_vacia)
    assert len(rows) == 1
    assert rows[0]["rfc"] == "MNO050505XX5"


@pytest.mark.parametrize("situacion_cruda,substate_esperado", [
    ("Presunto", "presunto"),
    ("Presuntos", "presunto"),
    ("Desvirtuado", "desvirtuado"),
    ("Definitivo", "definitivo"),
    ("Definitivos", "definitivo"),
    ("Sentencia favorable", "sentencia_favorable"),
])
def test_parse_art_69b_mapea_todas_las_variantes_de_substate(tmp_path, situacion_cruda, substate_esperado):
    df = pd.DataFrame({
        "RFC": ["pqr060606xx6"],
        "Nombre del Contribuyente": ["Empresa de Prueba SA de CV"],
        "Situación del Contribuyente": [situacion_cruda],
    })
    path = tmp_path / "art69b_variante.xlsx"
    df.to_excel(path, index=False)
    rows = parse_art_69b(str(path))
    assert rows[0]["art69b_substate"] == substate_esperado
