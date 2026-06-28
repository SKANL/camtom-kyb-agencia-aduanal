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
        for dt in ("csf", "acta_constitutiva", "rfc")
        if dt in documentos
    ]

    razon_social_csf = (documentos.get("csf", {}).get("fields") or {}).get(
        "razon_social", expediente["razon_social"]
    )
    sim_razon_social = comparar_semanticamente(
        supabase_client, "razón social", expediente["razon_social"], razon_social_csf
    )

    domicilio_comprobante = (
        documentos.get("comprobante_domicilio", {}).get("fields") or {}
    ).get("domicilio", expediente.get("domicilio_fiscal") or "")
    sim_domicilio = comparar_semanticamente(
        supabase_client,
        "domicilio",
        expediente.get("domicilio_fiscal") or "",
        domicilio_comprobante,
    )

    rep_poder = (documentos.get("poder_notarial", {}).get("fields") or {}).get(
        "nombre_representante", expediente.get("representante_legal") or ""
    )
    sim_representante = comparar_semanticamente(
        supabase_client,
        "nombre de representante legal",
        expediente.get("representante_legal") or "",
        rep_poder,
    )

    return reconciliar(rfcs, sim_razon_social, sim_domicilio, sim_representante, fechas_validas=True)
