from datetime import date, datetime, timezone
from domain.scoring.factors import factores_listas_sat, factores_discrepancias, factores_completitud
from domain.scoring.engine import evaluar
from domain.scoring.lifecycle import necesita_actualizacion
from domain.scoring.acciones import acciones_para
from infrastructure.sat.lookup import consultar_rfc_en_listas

def evaluar_expediente(supabase_client, expediente_id: str, resultado_reconciliacion, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    expediente = supabase_client.table("expedientes").select("*").eq("id", expediente_id).execute().data[0]
    documentos = supabase_client.table("documentos").select("*").eq("expediente_id", expediente_id).execute().data
    socios = supabase_client.table("socios").select("*").eq("expediente_id", expediente_id).execute().data

    sat_hits = consultar_rfc_en_listas(supabase_client, expediente_id, expediente["rfc"])
    factores = factores_listas_sat(sat_hits) + factores_discrepancias(resultado_reconciliacion) + factores_completitud(documentos, socios, hoy)
    resultado = evaluar(factores)
    acciones = acciones_para([f.factor_code for f in resultado.factores])
    needs_update = necesita_actualizacion(documentos, None, hoy, cliente_reporto_cambio=False)

    supabase_client.table("evaluations").insert({
        "expediente_id": expediente_id, "score_total": resultado.score_total, "decision": resultado.decision,
        "critical_blocks": resultado.critical_blocks, "summary": {"acciones_sugeridas": acciones},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    supabase_client.table("expedientes").update({
        "decision": resultado.decision, "score_total": resultado.score_total,
        "status": "needs_update" if needs_update else "completed",
        "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", expediente_id).execute()

    return {"score_total": resultado.score_total, "decision": resultado.decision, "acciones_sugeridas": acciones, "needs_update": needs_update}
