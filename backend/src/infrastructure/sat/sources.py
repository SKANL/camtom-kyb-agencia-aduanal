from dataclasses import dataclass


@dataclass(frozen=True)
class SatSource:
    list_type: str
    url: str
    description: str


SAT_SOURCES: dict[str, SatSource] = {
    "art_69": SatSource(
        "art_69",
        "https://wwwmat.sat.gob.mx/consultas/11981/consulta-la-relacion-de-contribuyentes-incumplidos",
        "Contribuyentes incumplidos (Art. 69 CFF)",
    ),
    "art_69b": SatSource(
        "art_69b",
        "https://wwwmat.sat.gob.mx/consultas/76674/consulta-la-relacion-de-contribuyentes-con-operaciones-presuntamente-inexistentes",
        "EFOS (Art. 69-B CFF)",
    ),
    "art_69b_bis": SatSource(
        "art_69b_bis",
        "https://www.sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html",
        "Pérdidas fiscales indebidas (Art. 69-B Bis CFF)",
    ),
}
