import hashlib, json, uuid
from datetime import datetime, timezone
from typing import Callable

SCHEMA_VERSION = "v1"

def compute_input_hash(call_type: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(f"{call_type}:{SCHEMA_VERSION}:{canonical}".encode("utf-8")).hexdigest()

def call_with_harness(supabase_client, call_type: str, payload: dict, compute: Callable[[], dict], max_retries: int = 2) -> dict:
    input_hash = compute_input_hash(call_type, payload)
    cached = supabase_client.table("ai_call_cache").select("*").eq("input_hash", input_hash).execute()
    if cached.data:
        return cached.data[0]["result"]

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            result = compute()
            supabase_client.table("ai_call_cache").insert({
                "id": str(uuid.uuid4()), "input_hash": input_hash, "call_type": call_type,
                "schema_version": SCHEMA_VERSION, "result": result, "retries": attempt,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            return result
        except Exception as exc:  # noqa: BLE001 — frontera deliberada: cualquier falla cae al reintento
            last_error = exc
            continue
    raise RuntimeError(f"Harness: agotados los reintentos para {call_type}") from last_error
