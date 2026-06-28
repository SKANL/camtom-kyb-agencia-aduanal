#!/usr/bin/env python
"""Importa los archivos CSV del SAT (Datos Abiertos) a Supabase.

Uso:
    uv run python scripts/import_sat_data.py

Requiere:
    - SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en backend/.env
    - Archivos CSV descargados en backend/data/sat/ (estructura completa)

Flujo:
    1. Agrupa archivos CSV por list_type (art_69, art_69b, art_69b_bis)
    2. Parsea cada archivo con parse_sat_csv()
    3. Mergea todos los registros del mismo list_type
    4. Inserta en lote en sat_lista_registros (atomic replace por list_type)
    5. Registra cada import en sat_import_runs
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Asegurar que backend/ esté en sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from supabase import create_client

from src.infrastructure.sat.ingest import bulk_import_csvs


def main():
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    print("Iniciando importación masiva de datos SAT...")
    print()

    results = bulk_import_csvs(supabase)

    print()
    print("=" * 60)
    print("IMPORTACIÓN COMPLETADA")
    print("=" * 60)
    for list_type, result in results.items():
        print(f"  {list_type}: {result['rows_imported']} registros (run_id={result['run_id']})")

    total = sum(r["rows_imported"] for r in results.values())
    print(f"\n  TOTAL: {total} registros importados de datos reales del SAT.")


if __name__ == "__main__":
    main()
