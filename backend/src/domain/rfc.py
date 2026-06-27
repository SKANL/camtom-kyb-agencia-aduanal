import re
from datetime import date

_RFC_MORAL_REGEX = re.compile(r"^[A-ZÑ&]{3}(\d{2})(\d{2})(\d{2})[A-Z0-9]{3}$")

def normalize_rfc(raw: str) -> str:
    return raw.strip().upper().replace(" ", "").replace("-", "")

def validar_estructura(rfc: str) -> bool:
    rfc = normalize_rfc(rfc)
    if len(rfc) != 12:
        return False
    match = _RFC_MORAL_REGEX.match(rfc)
    if not match:
        return False
    yy, mm, dd = (int(g) for g in match.groups())
    for century in (2000, 1900):
        try:
            date(century + yy, mm, dd)
            return True
        except ValueError:
            continue
    return False
