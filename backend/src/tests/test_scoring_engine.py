from domain.scoring.engine import evaluar
from domain.scoring.factors import Factor

def test_sin_factores_es_safe():
    assert evaluar([]).decision == "safe"

def test_50_puntos_es_review_required_caso_demo_2():
    r = evaluar([Factor("doc_expired", 20, False, "x"), Factor("disc_razon_social", 30, False, "y")])
    assert r.score_total == 50 and r.decision == "review_required"

def test_bloqueo_critico_fuerza_high_risk_sin_importar_score():
    assert evaluar([Factor("sat_69b_definitivo", 100, True, "x")]).decision == "high_risk"

def test_rfc_invalido_fuerza_piso_review_required():
    assert evaluar([Factor("rfc_formato_invalido", 60, False, "x")]).decision == "review_required"
