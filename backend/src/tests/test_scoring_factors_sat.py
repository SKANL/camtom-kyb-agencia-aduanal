from domain.scoring.factors import factores_listas_sat

def test_rfc_invalido_solo_genera_ese_factor():
    factores = factores_listas_sat([{"factor_code": "rfc_formato_invalido", "rfc": "ABC123"}])
    assert [f.factor_code for f in factores] == ["rfc_formato_invalido"]
    assert factores[0].points == 60

def test_sin_hits_solo_genera_art_49bis():
    factores = factores_listas_sat([])
    assert len(factores) == 1 and factores[0].factor_code == "art_49bis_no_verificable" and factores[0].points == 0

def test_69b_definitivo_es_bloqueo_critico():
    factores = factores_listas_sat([{"list_type": "art_69b", "match_substate": "definitivo"}])
    bloqueo = next(f for f in factores if f.factor_code == "sat_69b_definitivo")
    assert bloqueo.is_critical_block is True and bloqueo.points == 100
