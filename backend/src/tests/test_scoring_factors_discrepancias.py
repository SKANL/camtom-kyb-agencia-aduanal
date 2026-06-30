"""TDD coverage for factores_discrepancias — previously had zero tests."""
from types import SimpleNamespace
import pytest
from domain.scoring.factors import factores_discrepancias


def _resultado(**flags):
    defaults = dict(
        rfc_discrepante=False,
        razon_social_discrepante=False,
        domicilio_discrepante=False,
        representante_discrepante=False,
        fechas_inconsistentes=False,
    )
    defaults.update(flags)
    return SimpleNamespace(**defaults)


def test_all_clean_returns_empty():
    factores = factores_discrepancias(_resultado())
    assert factores == []


def test_rfc_discrepante_adds_disc_rfc():
    factores = factores_discrepancias(_resultado(rfc_discrepante=True))
    codes = [f.factor_code for f in factores]
    assert codes == ["disc_rfc"]
    assert factores[0].points == 50


def test_razon_social_discrepante_adds_factor():
    factores = factores_discrepancias(_resultado(razon_social_discrepante=True))
    codes = [f.factor_code for f in factores]
    assert "disc_razon_social" in codes
    pts = {f.factor_code: f.points for f in factores}
    assert pts["disc_razon_social"] == 30


def test_domicilio_discrepante_adds_factor():
    factores = factores_discrepancias(_resultado(domicilio_discrepante=True))
    codes = [f.factor_code for f in factores]
    assert "disc_domicilio" in codes
    assert {f.factor_code: f.points for f in factores}["disc_domicilio"] == 20


def test_representante_discrepante_adds_factor():
    factores = factores_discrepancias(_resultado(representante_discrepante=True))
    codes = [f.factor_code for f in factores]
    assert "disc_representante" in codes
    assert {f.factor_code: f.points for f in factores}["disc_representante"] == 25


def test_fechas_inconsistentes_adds_factor():
    factores = factores_discrepancias(_resultado(fechas_inconsistentes=True))
    codes = [f.factor_code for f in factores]
    assert "disc_fechas" in codes
    assert {f.factor_code: f.points for f in factores}["disc_fechas"] == 15


def test_all_flags_true_returns_five_factors():
    factores = factores_discrepancias(_resultado(
        rfc_discrepante=True,
        razon_social_discrepante=True,
        domicilio_discrepante=True,
        representante_discrepante=True,
        fechas_inconsistentes=True,
    ))
    assert len(factores) == 5
    total = sum(f.points for f in factores)
    assert total == 50 + 30 + 20 + 25 + 15  # 140 pts


def test_none_are_critical_blocks():
    factores = factores_discrepancias(_resultado(
        rfc_discrepante=True, razon_social_discrepante=True,
    ))
    assert all(not f.is_critical_block for f in factores)
