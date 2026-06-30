"""
Seed demo data directly into Supabase for the KYB platform demo.

Creates 3 complete expedientes with all documents, fields, socios, and runs
evaluation. Uses pre-computed fields (extraction_status=human_reviewed) to
bypass the AI extraction step — results are deterministic.

Usage:
  cd backend
  uv run python scripts/seed_demo_data.py

Optional: clear existing demo data first with --clean flag:
  uv run python scripts/seed_demo_data.py --clean
"""

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]


def make_id() -> str:
    return str(uuid.uuid4())


def seed(supabase):
    # ── Scenario 1: CLEAN — EKU9003173C9 ──────────────────────────────────────
    exp1_id = make_id()
    supabase.table("expedientes").insert({
        "id": exp1_id,
        "razon_social": "Escuela Kemper Urgate SA de CV",
        "rfc": "EKU9003173C9",
        "domicilio_fiscal": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
        "representante_legal": "Juan Pérez García",
        "status": "pending",
        "decision": None,
        "score_total": None,
    }).execute()

    docs1 = [
        {"doc_type": "csf", "fields": {
            "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV",
            "domicilio_fiscal": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
            "fecha_emision": "2026-06-01", "regimen_fiscal": "601 - General de Ley Personas Morales",
        }},
        {"doc_type": "acta_constitutiva", "fields": {
            "rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV",
            "socios": [{"nombre": "Juan Pérez García", "rfc": "PEGJ850101HDF", "porcentaje": 60},
                       {"nombre": "María López Ramírez", "rfc": "LORM900215MDF", "porcentaje": 40}],
        }},
        {"doc_type": "comprobante_domicilio", "fields": {
            "domicilio": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
            "fecha_emision": "2026-06-01",
        }},
        {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": True}},
        {"doc_type": "identificacion_rep_legal", "fields": {
            "nombre_completo": "Juan Pérez García", "fecha_vencimiento": "2029-12-31",
        }},
        {"doc_type": "poder_notarial", "fields": {
            "nombre_representante": "Juan Pérez García", "alcance": "Actos de Administración y Dominio",
        }},
        {"doc_type": "encargo_conferido", "fields": {
            "rfc_agente_aduanal": "CAMT930401AB9",
            "alcance": "Importación y Exportación de mercancías en general",
            "fecha_vigencia": "2027-12-31",
        }},
        {"doc_type": "rfc", "fields": {}},
    ]
    for d in docs1:
        supabase.table("documentos").insert({
            "id": make_id(), "expediente_id": exp1_id,
            "doc_type": d["doc_type"], "entry_method": "uploaded",
            "extraction_status": "human_reviewed", "human_reviewed": True,
            "fields": d["fields"],
        }).execute()

    supabase.table("socios").insert([
        {"id": make_id(), "expediente_id": exp1_id, "nombre": "Juan Pérez García",
         "rfc": "PEGJ850101HDF", "porcentaje": 60},
        {"id": make_id(), "expediente_id": exp1_id, "nombre": "María López Ramírez",
         "rfc": "LORM900215MDF", "porcentaje": 40},
    ]).execute()

    # ── Scenario 2: DISCREPANCY — COX010101AB1 ────────────────────────────────
    exp2_id = make_id()
    supabase.table("expedientes").insert({
        "id": exp2_id,
        "razon_social": "Corporativo X SA de CV",
        "rfc": "COX010101AB1",
        "domicilio_fiscal": "Avenida Insurgentes Sur Num 123, Colonia Roma",
        "representante_legal": "María López",
        "status": "pending",
        "decision": None,
        "score_total": None,
    }).execute()

    docs2 = [
        {"doc_type": "csf", "fields": {
            "rfc": "COX010101AB1", "razon_social": "Corporativo Equis Distribuidora, SA de CV",
            "domicilio_fiscal": "Avenida Insurgentes Sur Num 123, Colonia Roma",
            "fecha_emision": "2026-06-01", "regimen_fiscal": "601 - General de Ley Personas Morales",
        }},
        {"doc_type": "acta_constitutiva", "fields": {
            "rfc": "COX010101AB1",
            "razon_social": "Corporativo X, S.A. de C.V.",
            "socios": [{"nombre": "María López Hernandez", "rfc": "LOHM750310MDF", "porcentaje": 51},
                       {"nombre": "Roberto Sánchez Cruz", "rfc": "SACR800520HDF", "porcentaje": 49}],
        }},
        {"doc_type": "comprobante_domicilio", "fields": {
            "domicilio": "Insurgentes Sur 123, Roma",
            "fecha_emision": "2026-06-01",
        }},
        {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": True}},
        {"doc_type": "identificacion_rep_legal", "fields": {
            "nombre_completo": "Maria Lopez Hernandez", "fecha_vencimiento": "2028-06-30",
        }},
        {"doc_type": "poder_notarial", "fields": {
            "nombre_representante": "Carlos Eduardo Morales Ríos",
            "alcance": "Actos de Administración",
        }},
        {"doc_type": "encargo_conferido", "fields": {
            "rfc_agente_aduanal": "CAMT930401AB9",
            "alcance": "Importación y Exportación de mercancías en general",
            "fecha_vigencia": "2027-06-30",
        }},
        {"doc_type": "rfc", "fields": {}},
    ]
    for d in docs2:
        supabase.table("documentos").insert({
            "id": make_id(), "expediente_id": exp2_id,
            "doc_type": d["doc_type"], "entry_method": "uploaded",
            "extraction_status": "human_reviewed", "human_reviewed": True,
            "fields": d["fields"],
        }).execute()

    supabase.table("socios").insert([
        {"id": make_id(), "expediente_id": exp2_id, "nombre": "María López Hernandez",
         "rfc": "LOHM750310MDF", "porcentaje": 51},
        {"id": make_id(), "expediente_id": exp2_id, "nombre": "Roberto Sánchez Cruz",
         "rfc": "SACR800520HDF", "porcentaje": 49},
    ]).execute()

    # ── Scenario 3: HIGH RISK — AAA120730823 ───────────────────────────────────
    exp3_id = make_id()
    supabase.table("expedientes").insert({
        "id": exp3_id,
        "razon_social": "Empresa en Lista Negra SA de CV",
        "rfc": "AAA120730823",
        "domicilio_fiscal": "Calle Reforma 456, Col. Centro, CDMX, CP 06000",
        "representante_legal": "Carlos Sánchez",
        "status": "pending",
        "decision": None,
        "score_total": None,
    }).execute()

    docs3 = [
        {"doc_type": "csf", "fields": {
            "rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV",
            "domicilio_fiscal": "Calle Reforma 456, Col. Centro, CDMX, CP 06000",
            "fecha_emision": "2026-06-01", "regimen_fiscal": "601 - General de Ley Personas Morales",
        }},
        {"doc_type": "acta_constitutiva", "fields": {
            "rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV",
            "socios": [{"nombre": "Carlos Sánchez", "rfc": "SACC800401HDF", "porcentaje": 100}],
        }},
        {"doc_type": "comprobante_domicilio", "fields": {
            "domicilio": "Calle Reforma 456, Col. Centro, CDMX, CP 06000",
            "fecha_emision": "2026-06-01",
        }},
        {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": False}},
        {"doc_type": "identificacion_rep_legal", "fields": {
            "nombre_completo": "Carlos Sánchez", "fecha_vencimiento": "2027-09-15",
        }},
        {"doc_type": "poder_notarial", "fields": {
            "nombre_representante": "Carlos Sánchez", "alcance": "Actos de Administración y Dominio",
        }},
        {"doc_type": "encargo_conferido", "fields": {
            "rfc_agente_aduanal": "CAMT930401AB9",
            "alcance": "Importación y Exportación",
            "fecha_vigencia": "2027-01-31",
        }},
        {"doc_type": "rfc", "fields": {}},
    ]
    for d in docs3:
        supabase.table("documentos").insert({
            "id": make_id(), "expediente_id": exp3_id,
            "doc_type": d["doc_type"], "entry_method": "uploaded",
            "extraction_status": "human_reviewed", "human_reviewed": True,
            "fields": d["fields"],
        }).execute()

    supabase.table("socios").insert([
        {"id": make_id(), "expediente_id": exp3_id, "nombre": "Carlos Sánchez",
         "rfc": "SACC800401HDF", "porcentaje": 100},
    ]).execute()

    return exp1_id, exp2_id, exp3_id


def clean_demo_data(supabase):
    """Delete expedientes with the demo RFC values."""
    demo_rfcs = ["EKU9003173C9", "COX010101AB1", "AAA120730823"]
    for rfc in demo_rfcs:
        rows = supabase.table("expedientes").select("id").eq("rfc", rfc).execute().data
        for row in rows:
            exp_id = row["id"]
            supabase.table("documentos").delete().eq("expediente_id", exp_id).execute()
            supabase.table("socios").delete().eq("expediente_id", exp_id).execute()
            supabase.table("evaluations").delete().eq("expediente_id", exp_id).execute()
            supabase.table("consultas_sat").delete().eq("expediente_id", exp_id).execute()
            supabase.table("expedientes").delete().eq("id", exp_id).execute()
    print("Demo data cleaned.")


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    if "--clean" in sys.argv:
        clean_demo_data(supabase)
        return

    print("Seeding demo expedientes...")
    exp1_id, exp2_id, exp3_id = seed(supabase)

    # Run evaluations via the service layer
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from services.evaluation_service import evaluar_expediente
    from services.reconciliation_service import reconciliar_expediente

    for exp_id, name in [(exp1_id, "Escenario 1 — Limpio"), (exp2_id, "Escenario 2 — Discrepancia"), (exp3_id, "Escenario 3 — Alto Riesgo")]:
        try:
            recon = reconciliar_expediente(supabase, exp_id)
            result = evaluar_expediente(supabase, exp_id, recon)
            print(f"  {name}: score={result['score_total']} decision={result['decision']}")
        except Exception as e:
            print(f"  {name}: evaluation failed — {e}")

    print("\nDone. Open the frontend to see the seeded expedientes.")


if __name__ == "__main__":
    main()
