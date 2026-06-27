from domain.rfc import normalize_rfc, validar_estructura

def test_normalize_rfc_strips_and_uppercases():
    assert normalize_rfc(" eku900317-3c9 ") == "EKU9003173C9"

def test_validar_estructura_rfc_valido_sandbox_sat():
    assert validar_estructura("EKU9003173C9") is True

def test_validar_estructura_rechaza_fecha_imposible():
    assert validar_estructura("ABC991399XXX") is False

def test_validar_estructura_rechaza_longitud_incorrecta():
    assert validar_estructura("ABC123") is False
