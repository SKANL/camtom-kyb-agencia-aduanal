#!/usr/bin/env python
"""Descarga los archivos CSV del SAT (Datos Abiertos) a backend/data/sat/.

Uso:
    uv run python scripts/download_sat_data.py

Requiere: curl o python requests (incluido en stdlib).
"""

import os
import urllib.request

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sat")

# Mapeo: (ruta_destino, url)
FILES = [
    # 69-B CFF (EFOS)
    ("articulo-69b-cff/Listado_completo_69-B.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/Listado_completo_69-B.csv"),
    ("articulo-69b-cff/Definitivos.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/Definitivos.csv"),
    ("articulo-69b-cff/Presuntos.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/Presuntos.csv"),
    ("articulo-69b-cff/Desvirtuados.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/Desvirtuados.csv"),
    ("articulo-69b-cff/SentenciasFavorables.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/SentenciasFavorables.csv"),

    # 69-B Bis CFF
    ("articulo-69b-bis-cff/Listado_69_B_Bis_Completo.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGGC/Listado_69_B_Bis_Completo.csv"),
    ("articulo-69b-bis-cff/Listado_69_B_Bis_Definitivo.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGGC/Listado_69_B_Bis_Definitivo.csv"),
    ("articulo-69b-bis-cff/Listado_69_B_Bis_SentenciaFa.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGGC/Listado_69_B_Bis_SentenciaFa.csv"),

    # 69 CFF — Contribuyentes incumplidos
    ("articulo-69-cff/contribuyentes-incumplidos/Cancelados.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/Cancelados.csv"),
    ("articulo-69-cff/contribuyentes-incumplidos/Firmes.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/Firmes.csv"),
    ("articulo-69-cff/contribuyentes-incumplidos/Exigibles.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/Exigibles.csv"),
    ("articulo-69-cff/contribuyentes-incumplidos/CSDsinefectos.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/CSDsinefectos.csv"),
    ("articulo-69-cff/contribuyentes-incumplidos/No_localizados.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/No_localizados.csv"),
    ("articulo-69-cff/contribuyentes-incumplidos/EntespublicosydeGobiernoomisos.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/EntespublicosydeGobiernoomisos.csv"),
    ("articulo-69-cff/contribuyentes-incumplidos/Sentencias.csv",
     "https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/Sentencias.csv"),
]


def main():
    for rel_path, url in FILES:
        dest = os.path.normpath(os.path.join(BASE_DIR, rel_path))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print(f"Descargando {rel_path}...")
        try:
            urllib.request.urlretrieve(url, dest)
            size_kb = os.path.getsize(dest) / 1024
            print(f"  OK ({size_kb:.0f} KB)")
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
