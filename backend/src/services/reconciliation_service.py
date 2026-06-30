from domain.reconciliation.reconcile import reconciliar
from infrastructure.ai.similarity import comparar_semanticamente


def reconciliar_expediente(supabase_client, expediente_id: str):
    result = (
        supabase_client.table("expedientes")
        .select("*")
        .eq("id", expediente_id)
        .execute()
    )
    if not result.data:
        raise ValueError(f"Expediente {expediente_id!r} no encontrado")
    expediente = result.data[0]
    documentos = {
        d["doc_type"]: d
        for d in supabase_client.table("documentos")
        .select("*")
        .eq("expediente_id", expediente_id)
        .execute()
        .data
    }

    rfcs = [expediente["rfc"]] + [
        (documentos[dt].get("fields") or {}).get("rfc", expediente["rfc"])
        for dt in ("csf", "acta_constitutiva")
        if dt in documentos
    ]

    razon_social_csf = (documentos.get("csf", {}).get("fields") or {}).get(
        "razon_social", expediente["razon_social"]
    )
    sim_razon_social = comparar_semanticamente(
        supabase_client, "razón social", expediente["razon_social"], razon_social_csf
    )

    domicilio_a = expediente.get("domicilio_fiscal") or ""
    domicilio_b = (documentos.get("comprobante_domicilio", {}).get("fields") or {}).get("domicilio", domicilio_a)
    sim_domicilio = (
        comparar_semanticamente(supabase_client, "domicilio", domicilio_a, domicilio_b)
        if (domicilio_a or domicilio_b)
        else {"similarity": 1.0, "same_entity": True, "reasoning": "Sin datos de domicilio para comparar"}
    )

    rep_a = expediente.get("representante_legal") or ""
    rep_b = (documentos.get("poder_notarial", {}).get("fields") or {}).get("nombre_representante", rep_a)
    sim_representante = (
        comparar_semanticamente(supabase_client, "nombre de representante legal", rep_a, rep_b)
        if (rep_a or rep_b)
        else {"similarity": 1.0, "same_entity": True, "reasoning": "Sin datos de representante para comparar"}
    )

    compared_values: dict = {}
    if razon_social_csf != expediente["razon_social"]:
        compared_values["razon_social"] = {
            "expediente": expediente["razon_social"],
            "documento": razon_social_csf,
            "documento_id": documentos.get("csf", {}).get("id"),
        }
    if domicilio_b and domicilio_a != domicilio_b:
        compared_values["domicilio"] = {
            "expediente": domicilio_a,
            "documento": domicilio_b,
            "documento_id": documentos.get("comprobante_domicilio", {}).get("id"),
        }
    if rep_b and rep_a != rep_b:
        compared_values["representante"] = {
            "expediente": rep_a,
            "documento": rep_b,
            "documento_id": documentos.get("poder_notarial", {}).get("id"),
        }
    rfcs_norm = {r.strip().upper() for r in rfcs if r}
    if len(rfcs_norm) > 1:
        compared_values["rfc"] = {
            "expediente": rfcs[0] if rfcs else "",
            "documento": ", ".join(sorted(rfcs_norm - {rfcs[0].strip().upper() if rfcs else ""})),
            "documento_id": None,
        }

    return reconciliar(rfcs, sim_razon_social, sim_domicilio, sim_representante, fechas_validas=True, compared_values=compared_values)
