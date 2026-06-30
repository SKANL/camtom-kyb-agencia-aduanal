import os
import tempfile
import uuid
import uuid as _uuid
from datetime import datetime, timezone, date as _date

from fastapi import APIRouter, UploadFile, Depends
from src.api.deps import get_supabase_client
from src.infrastructure.sat.ingest import ingest_list

router = APIRouter(prefix="/admin", tags=["admin"])

DEMO_RFCS = ["EKU9003173C9", "COX010101AB1", "AAA120730823"]


def _clean_demo(supabase):
    for rfc in DEMO_RFCS:
        rows = supabase.table("expedientes").select("id").eq("rfc", rfc).execute().data
        for row in rows:
            exp_id = row["id"]
            for tbl in ("documentos", "socios", "evaluations", "consultas_sat"):
                supabase.table(tbl).delete().eq("expediente_id", exp_id).execute()
            supabase.table("expedientes").delete().eq("id", exp_id).execute()


def _make_id():
    return str(_uuid.uuid4())


def _seed_expediente(supabase, razon_social, rfc, domicilio, representante, docs, socios_data):
    exp_id = _make_id()
    supabase.table("expedientes").insert({
        "id": exp_id, "razon_social": razon_social, "rfc": rfc,
        "domicilio_fiscal": domicilio, "representante_legal": representante,
        "status": "pending", "decision": None, "score_total": None,
    }).execute()
    for d in docs:
        supabase.table("documentos").insert({
            "id": _make_id(), "expediente_id": exp_id,
            "doc_type": d["doc_type"], "entry_method": "uploaded",
            "extraction_status": "human_reviewed", "human_reviewed": True,
            "fields": d["fields"],
        }).execute()
    if socios_data:
        supabase.table("socios").insert([
            {"id": _make_id(), "expediente_id": exp_id, **s} for s in socios_data
        ]).execute()
    return exp_id


@router.post("/demo/seed")
def seed_demo(supabase=Depends(get_supabase_client)):
    """Seed 3 demo expedientes deterministically. Cleans previous demo data first."""
    _clean_demo(supabase)
    hoy = str(_date.today())

    exp1_id = _seed_expediente(
        supabase,
        razon_social="Escuela Kemper Urgate SA de CV",
        rfc="EKU9003173C9",
        domicilio="Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
        representante="Juan Pérez García",
        docs=[
            {"doc_type": "csf", "fields": {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV", "domicilio_fiscal": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700", "fecha_emision": hoy, "regimen_fiscal": "601 - General de Ley Personas Morales"}},
            {"doc_type": "acta_constitutiva", "fields": {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV", "socios": [{"nombre": "Juan Pérez García", "rfc": "PEGJ850101HDF", "porcentaje": 60}, {"nombre": "María López Ramírez", "rfc": "LORM900215MDF", "porcentaje": 40}]}},
            {"doc_type": "comprobante_domicilio", "fields": {"domicilio": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700", "fecha_emision": hoy}},
            {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": True}},
            {"doc_type": "identificacion_rep_legal", "fields": {"nombre_completo": "Juan Pérez García", "fecha_vencimiento": "2029-12-31"}},
            {"doc_type": "poder_notarial", "fields": {"nombre_representante": "Juan Pérez García", "alcance": "Actos de Administración y Dominio"}},
            {"doc_type": "encargo_conferido", "fields": {"rfc_agente_aduanal": "CAMT930401AB9", "alcance": "Importación y Exportación", "fecha_vigencia": "2027-12-31"}},
            {"doc_type": "rfc", "fields": {"rfc": "EKU9003173C9", "razon_social": "Escuela Kemper Urgate SA de CV", "domicilio_fiscal": "Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700"}},
        ],
        socios_data=[
            {"nombre": "Juan Pérez García", "rfc": "PEGJ850101HDF", "porcentaje": 60},
            {"nombre": "María López Ramírez", "rfc": "LORM900215MDF", "porcentaje": 40},
        ],
    )

    exp2_id = _seed_expediente(
        supabase,
        razon_social="Corporativo X SA de CV",
        rfc="COX010101AB1",
        domicilio="Avenida Insurgentes Sur Num 123, Colonia Roma",
        representante="María López",
        docs=[
            {"doc_type": "csf", "fields": {"rfc": "COX010101AB1", "razon_social": "Corporativo X SA de CV", "domicilio_fiscal": "Avenida Insurgentes Sur Num 123, Colonia Roma", "fecha_emision": hoy, "regimen_fiscal": "601 - General de Ley Personas Morales"}},
            {"doc_type": "acta_constitutiva", "fields": {"rfc": "COX010101AB1", "razon_social": "Corporativo X, S.A. de C.V.", "socios": [{"nombre": "María López Hernandez", "rfc": "LOHM750310MDF", "porcentaje": 51}, {"nombre": "Roberto Sánchez Cruz", "rfc": "SACR800520HDF", "porcentaje": 49}]}},
            {"doc_type": "comprobante_domicilio", "fields": {"domicilio": "Insurgentes Sur 123, Roma", "fecha_emision": hoy}},
            {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": True}},
            {"doc_type": "identificacion_rep_legal", "fields": {"nombre_completo": "Maria Lopez Hernandez", "fecha_vencimiento": "2028-06-30"}},
            {"doc_type": "poder_notarial", "fields": {"nombre_representante": "Maria Lopez Hernandez", "alcance": "Actos de Administración"}},
            {"doc_type": "encargo_conferido", "fields": {"rfc_agente_aduanal": "CAMT930401AB9", "alcance": "Importación y Exportación", "fecha_vigencia": "2027-06-30"}},
            {"doc_type": "rfc", "fields": {"rfc": "COX010101AB1", "razon_social": "Corporativo X SA de CV", "domicilio_fiscal": "Avenida Insurgentes Sur Num 123, Colonia Roma"}},
        ],
        socios_data=[
            {"nombre": "María López Hernandez", "rfc": "LOHM750310MDF", "porcentaje": 51},
            {"nombre": "Roberto Sánchez Cruz", "rfc": "SACR800520HDF", "porcentaje": 49},
        ],
    )

    exp3_id = _seed_expediente(
        supabase,
        razon_social="Empresa en Lista Negra SA de CV",
        rfc="AAA120730823",
        domicilio="Calle Reforma 456, Col. Centro, CDMX, CP 06000",
        representante="Carlos Sánchez",
        docs=[
            {"doc_type": "csf", "fields": {"rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV", "domicilio_fiscal": "Calle Reforma 456, Col. Centro, CDMX, CP 06000", "fecha_emision": hoy, "regimen_fiscal": "601 - General de Ley Personas Morales"}},
            {"doc_type": "acta_constitutiva", "fields": {"rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV", "socios": [{"nombre": "Carlos Sánchez", "rfc": "SACC800401HDF", "porcentaje": 100}]}},
            {"doc_type": "comprobante_domicilio", "fields": {"domicilio": "Calle Reforma 456, Col. Centro, CDMX, CP 06000", "fecha_emision": hoy}},
            {"doc_type": "manifestacion_protesta", "fields": {"declara_no_69b_49bis": False}},
            {"doc_type": "identificacion_rep_legal", "fields": {"nombre_completo": "Carlos Sánchez", "fecha_vencimiento": "2027-09-15"}},
            {"doc_type": "poder_notarial", "fields": {"nombre_representante": "Carlos Sánchez", "alcance": "Actos de Administración y Dominio"}},
            {"doc_type": "encargo_conferido", "fields": {"rfc_agente_aduanal": "CAMT930401AB9", "alcance": "Importación y Exportación", "fecha_vigencia": "2027-01-31"}},
            {"doc_type": "rfc", "fields": {"rfc": "AAA120730823", "razon_social": "Empresa en Lista Negra SA de CV", "domicilio_fiscal": "Calle Reforma 456, Col. Centro, CDMX, CP 06000"}},
        ],
        socios_data=[{"nombre": "Carlos Sánchez", "rfc": "SACC800401HDF", "porcentaje": 100}],
    )

    # Run evaluations
    from services.evaluation_service import evaluar_expediente
    from services.reconciliation_service import reconciliar_expediente
    evaluations = []
    for exp_id in [exp1_id, exp2_id, exp3_id]:
        try:
            recon = reconciliar_expediente(supabase, exp_id)
            result = evaluar_expediente(supabase, exp_id, recon)
            evaluations.append({"expediente_id": exp_id, "decision": result["decision"], "score_total": result["score_total"]})
        except Exception as e:
            evaluations.append({"expediente_id": exp_id, "error": str(e)})

    return {
        "expediente_ids": [exp1_id, exp2_id, exp3_id],
        "evaluations": evaluations,
        "message": "3 expedientes demo cargados y evaluados",
    }


@router.post("/sat/ingest/{list_type}")
async def ingest_sat_list(list_type: str, file: UploadFile, supabase=Depends(get_supabase_client)):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        return ingest_list(supabase, list_type, tmp_path)
    finally:
        os.unlink(tmp_path)


@router.get("/sat-import-runs")
def list_sat_import_runs(supabase=Depends(get_supabase_client)):
    result = (
        supabase.table("sat_import_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(50)
        .execute()
    )
    return result.data


@router.post("/ingest/{list_type}")
def trigger_ingest_demo(list_type: str, supabase=Depends(get_supabase_client)):
    """Demo endpoint — records an import run without requiring file upload."""
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    run = {
        "id": run_id,
        "list_type": list_type,
        "status": "completed",
        "rows_imported": 0,
        "started_at": now,
        "finished_at": now,
    }
    supabase.table("sat_import_runs").insert(run).execute()
    return run
