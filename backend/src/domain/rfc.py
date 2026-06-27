import re
from datetime import date

_RFC_MORAL_REGEX = re.compile(r"^[A-ZÑ&]{3}(\d{2})(\d{2})(\d{2})[A-Z0-9]{3}$")

# Tabla de valores por caracter para el calculo del digito verificador
# (modulo 11), tal como la especifica el algoritmo oficial del SAT y la
# implementa la libreria de referencia python-stdnum (stdnum/mx/rfc.py).
_ALFABETO_DIGITO_VERIFICADOR = "0123456789ABCDEFGHIJKLMN&OPQRSTUVWXYZ Ñ"

def normalize_rfc(raw: str) -> str:
    """Limpia un RFC crudo: quita espacios y guiones, y lo pasa a mayusculas.

    No valida formato; solo normaliza la representacion para comparaciones
    y validaciones posteriores.
    """
    return raw.strip().upper().replace(" ", "").replace("-", "")

def _calcular_digito_verificador(rfc_sin_digito: str) -> str:
    """Calcula el digito verificador (modulo 11) para los primeros 11
    caracteres de un RFC de persona moral, siguiendo el mismo algoritmo
    que python-stdnum (stdnum/mx/rfc.py): se rellena a 12 caracteres con un
    espacio a la izquierda, se ponderan por posicion (peso 13-i) y se reduce
    modulo 11 sobre la tabla `_ALFABETO_DIGITO_VERIFICADOR`.
    """
    bloque = (" " + rfc_sin_digito)[-12:]
    suma = sum(
        _ALFABETO_DIGITO_VERIFICADOR.index(caracter) * (13 - posicion)
        for posicion, caracter in enumerate(bloque)
    )
    return _ALFABETO_DIGITO_VERIFICADOR[(11 - suma) % 11]

def validar_estructura(rfc: str) -> bool:
    """Valida que un RFC de persona moral tenga estructura correcta: 12
    caracteres, regex de letras/fecha/homoclave, fecha embebida calendario-
    valida y digito verificador correcto (modulo 11).

    Devuelve True si el RFC es estructuralmente valido, False en caso
    contrario.
    """
    rfc = normalize_rfc(rfc)
    if len(rfc) != 12:
        return False
    match = _RFC_MORAL_REGEX.match(rfc)
    if not match:
        return False
    yy, mm, dd = (int(g) for g in match.groups())
    fecha_valida = False
    # Se prueba primero el siglo 2000 y luego 1900: para personas morales
    # constituidas (no personas fisicas por edad), la inmensa mayoria de
    # RFCs activos en el padron del SAT corresponden a constituciones desde
    # el año 2000 en adelante, por lo que ese siglo es el candidato mas
    # probable cuando ambos resultan en una fecha calendario valida (p. ej.
    # yy="00"). Esta es una heuristica de desambiguacion, no una regla
    # oficial del SAT: el RFC no codifica el siglo de forma explicita.
    for century in (2000, 1900):
        try:
            date(century + yy, mm, dd)
            fecha_valida = True
            break
        except ValueError:
            continue
    if not fecha_valida:
        return False
    return rfc[-1] == _calcular_digito_verificador(rfc[:-1])
