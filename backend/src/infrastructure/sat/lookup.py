import uuid
from datetime import datetime, timezone

from src.domain.rfc import normalize_rfc, validar_estructura
from src.infrastructure.sat.parsers import es_unicamente_fraccion_vi
from src.infrastructure.sat.sources import SAT_SOURCES

# Listas registradas en SAT_SOURCES que todavia no tienen parser de ingesta
# (ver infrastructure.sat.ingest._PARSERS). Se excluyen explicitamente aqui
# en vez de comparar contra un literal string suelto en el loop: si se agrega
# un cuarto list_type sin parser, declararlo en este set es mas dificil de
# pasar por alto que un `if list_type == "...": continue` aislado, y un solo
# lugar documenta la razon (en vez de un comentario inline facil de borrar).
_LISTAS_SIN_PARSER = {"art_69b_bis"}


def consultar_rfc_en_listas(supabase_client, expediente_id: str, rfc: str) -> list[dict]:
    rfc = normalize_rfc(rfc)
    if not validar_estructura(rfc):
        return [{"factor_code": "rfc_formato_invalido", "rfc": rfc}]

    resultados = []
    for list_type, source in SAT_SOURCES.items():
        if list_type in _LISTAS_SIN_PARSER:
            continue
        resp = supabase_client.table("sat_lista_registros").select("*").eq("list_type", list_type).eq("rfc", rfc).execute()
        matches = resp.data

        found = len(matches) > 0
        excepcion_vi = list_type == "art_69" and found and all(es_unicamente_fraccion_vi(m.get("situacion", "")) for m in matches)

        import_run_id = _resolver_run_id_mas_reciente(supabase_client, list_type)

        supabase_client.table("consultas_sat").insert({
            "id": str(uuid.uuid4()), "expediente_id": expediente_id, "rfc_consultado": rfc,
            "list_type": list_type, "source_url": source.url, "found": found,
            "match_substate": matches[0].get("art69b_substate") if found else None,
            "match_detail": {"matches": matches} if found else None,
            "consulted_at": datetime.now(timezone.utc).isoformat(),
            "import_run_id": import_run_id,
        }).execute()

        if found and not excepcion_vi:
            resultados.append({"list_type": list_type, "match_substate": matches[0].get("art69b_substate")})
    return resultados


def _resolver_run_id_mas_reciente(supabase_client, list_type: str) -> str | None:
    """Resuelve el id del run mas reciente con status="success" para
    list_type, o None si nunca se corrio una ingesta exitosa para esa lista.

    Se ordena/recorta en Python (no via .order().limit() de PostgREST) a
    proposito: el FakeSupabase de tests/conftest.py implementa order() y
    limit() como no-ops, asi que depender de ellos haria el test pasar sin
    verificar nada real. Filtrar aqui evita ese falso positivo y evita tener
    que extender el fake compartido para esto.
    """
    resp = (
        supabase_client.table("sat_import_runs")
        .select("*")
        .eq("list_type", list_type)
        .eq("status", "success")
        .execute()
    )
    runs = resp.data
    if not runs:
        return None
    run_mas_reciente = max(runs, key=lambda r: r["started_at"])
    return run_mas_reciente["id"]
