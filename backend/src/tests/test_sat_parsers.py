import pandas as pd
import pytest
from infrastructure.sat.parsers import parse_art_69, es_unicamente_fraccion_vi


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


def test_es_unicamente_fraccion_vi_true():
    assert es_unicamente_fraccion_vi("VI") is True


def test_es_unicamente_fraccion_vi_false_con_otra_fraccion():
    assert es_unicamente_fraccion_vi("I; VI") is False
