"""
Seed script: creates the 3 demo expedientes in Supabase.

Prerequisites (run in order):
  1. Run the SAT ETL at least once so sat_lista_registros has art_69b data:
       curl -X POST https://backend-nine-snowy-67.vercel.app/admin/sat/ingest/art_69b \
            -F "file=@path/to/art_69b.xlsx"
     OR download the xlsx from the SAT and upload via the admin UI.
  2. Then run this script:
       cd backend && uv run python scripts/seed_demo.py

Environment variables required:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""

import os
import sys

from supabase import create_client

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)


def get_rfc_69b_definitivo() -> str:
    """Fetch a real RFC from the 69-B definitivos list (most recent import)."""
    result = (
        supabase.table("sat_lista_registros")
        .select("rfc")
        .eq("list_type", "art_69b")
        .eq("art69b_substate", "definitivo")
        .limit(1)
        .execute()
    )
    if not result.data:
        print(
            "ERROR: No se encontró ningún RFC en sat_lista_registros con "
            "list_type='art_69b' y art69b_substate='definitivo'.\n"
            "Ejecutá el ETL primero: POST /admin/sat/ingest/art_69b",
            file=sys.stderr,
        )
        sys.exit(1)
    return result.data[0]["rfc"]


def seed():
    rfc_high_risk = get_rfc_69b_definitivo()
    print(f"RFC high_risk obtenido del listado 69-B Definitivos: {rfc_high_risk}")

    demo_expedientes = [
        {
            "razon_social": "Escuela Kemper Urgate SA de CV",
            "rfc": "EKU9003173C9",
            "domicilio_fiscal": "Av. Insurgentes Sur 123, Col. Roma, CDMX",
            "representante_legal": "Juan Pérez García",
        },
        {
            "razon_social": "Corporativo X",
            "rfc": "COX010101AB1",
            "domicilio_fiscal": "Avenida Insurgentes Sur Num 123, Colonia Roma",
            "representante_legal": "María López",
        },
        {
            "razon_social": "Empresa en Lista Negra SA de CV",
            "rfc": rfc_high_risk,
            "domicilio_fiscal": "Calle Reforma 456, Col. Centro, CDMX",
            "representante_legal": "Carlos Sánchez",
        },
    ]

    inserted = 0
    for exp in demo_expedientes:
        # Avoid duplicate seeds
        existing = (
            supabase.table("expedientes")
            .select("id")
            .eq("rfc", exp["rfc"])
            .execute()
        )
        if existing.data:
            print(f"  SKIP — expediente con RFC {exp['rfc']} ya existe")
            continue
        result = supabase.table("expedientes").insert(exp).execute()
        print(f"  CREATED — {exp['rfc']}: {result.data[0]['id']}")
        inserted += 1

    print(f"\nSeed completado: {inserted} expediente(s) nuevos creados.")
    print("\nExpected decisions after evaluation:")
    print("  EKU9003173C9    → safe")
    print("  COX010101AB1    → review_required  (discrepancia razón social)")
    print(f"  {rfc_high_risk}  → high_risk  (en listado 69-B Definitivos)")


if __name__ == "__main__":
    seed()
