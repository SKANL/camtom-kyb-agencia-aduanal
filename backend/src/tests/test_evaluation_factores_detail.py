from domain.scoring.legal_refs import LEGAL_REFS


def test_legal_refs_has_sat_69b_definitivo():
    ref = LEGAL_REFS["sat_69b_definitivo"]
    assert ref["category"] == "sat"
    assert "69-B" in ref["ref"]


def test_legal_refs_has_disc_domicilio():
    ref = LEGAL_REFS["disc_domicilio"]
    assert ref["category"] == "discrepancia"
    assert "1.4.14" in ref["ref"]


def test_legal_refs_has_doc_missing():
    ref = LEGAL_REFS["doc_missing"]
    assert ref["category"] == "completitud"


def test_all_known_factor_codes_have_legal_ref():
    known = [
        "sat_69b_definitivo", "sat_69b_presunto", "sat_69b_bis", "sat_69_incumplido",
        "rfc_formato_invalido", "art_49bis_no_verificable",
        "disc_rfc", "disc_razon_social", "disc_domicilio", "disc_representante", "disc_fechas",
        "doc_missing", "doc_expired", "csf_stale", "doc_data_incomplete",
        "manifestacion_incompleta", "socios_incompletos", "rep_legal_incompleto",
    ]
    for code in known:
        assert code in LEGAL_REFS, f"Missing legal_ref for factor_code: {code}"
