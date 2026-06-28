from domain.reconciliation.reconcile import reconciliar

def test_rfc_discrepante_cuando_hay_mas_de_un_valor_distinto():
    r = reconciliar(["ABC010101XX1", "ABC010101XX1", "DEF020202XX2"],
                     {"similarity": 1.0, "same_entity": True}, {"similarity": 1.0, "same_entity": True},
                     {"similarity": 1.0, "same_entity": True}, True)
    assert r.rfc_discrepante is True

def test_razon_social_no_discrepante_si_similarity_supera_umbral():
    r = reconciliar(["X"], {"similarity": 0.92, "same_entity": False}, {"similarity": 1.0, "same_entity": True},
                     {"similarity": 1.0, "same_entity": True}, True)
    assert r.razon_social_discrepante is False

def test_domicilio_discrepante_con_umbral_mas_permisivo():
    r = reconciliar(["X"], {"similarity": 1.0, "same_entity": True}, {"similarity": 0.70, "same_entity": False},
                     {"similarity": 1.0, "same_entity": True}, True)
    assert r.domicilio_discrepante is True
