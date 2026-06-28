from src.domain.rfc import normalize_rfc, validar_estructura

def test_normalize_rfc_strips_and_uppercases():
    assert normalize_rfc(" eku900317-3c9 ") == "EKU9003173C9"

def test_validar_estructura_rfc_valido_sandbox_sat():
    assert validar_estructura("EKU9003173C9") is True

def test_validar_estructura_rechaza_fecha_imposible():
    assert validar_estructura("ABC991399XXX") is False

def test_validar_estructura_rechaza_longitud_incorrecta():
    assert validar_estructura("ABC123") is False

def test_validar_estructura_acepta_digito_verificador_correcto():
    # MAB9307148T4 es el ejemplo de referencia de python-stdnum (libreria
    # estandar de validacion de RFC): digito verificador "4" calculado por
    # modulo 11 sobre "MAB9307148T".
    assert validar_estructura("MAB9307148T4") is True

def test_validar_estructura_rechaza_digito_verificador_mutado():
    # Mismo RFC valido que el test anterior, pero con el ultimo caracter
    # (el digito verificador) mutado. El resto de la cadena queda intacto,
    # por lo que solo el chequeo de modulo 11 puede detectar el error.
    assert validar_estructura("MAB9307148T5") is False
