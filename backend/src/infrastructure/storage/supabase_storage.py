def crear_signed_upload_url(supabase_client, path: str) -> dict:
    resp = supabase_client.storage.from_("kyb-docs").create_signed_upload_url(path)
    return {"signed_url": resp["signed_url"], "token": resp.get("token")}
