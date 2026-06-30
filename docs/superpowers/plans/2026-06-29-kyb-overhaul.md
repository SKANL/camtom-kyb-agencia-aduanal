# KYB Platform Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 7 confirmed bugs (CORS on upload, silent scoring errors, broken SAT links, missing real-time UI) and 5 UX gaps (delete docs, inline edit, evidence rendering, nav actions, demo loader) with aggressive TDD throughout.

**Architecture:** Backend (FastAPI/Python) and Frontend (Next.js/TypeScript) are deployed as separate Vercel projects. Backend tasks are independent of frontend tasks — run them in parallel. After both complete, run E2E verification with seed data.

**Tech Stack:** Python 3.13 + uv + FastAPI + Supabase + Groq (LangChain) · Next.js App Router + TypeScript + Tailwind + shadcn/ui + SWR + Sonner

## Global Constraints

- Python: `uv run pytest src/tests/ -v` — never `pip`, never raw `python`
- Frontend: `pnpm` exclusively — never `npm` or `npx`
- TDD: write failing test → confirm failure → implement → confirm pass → commit
- No placeholder comments, no TODOs, no `any` in TypeScript without justification
- Commits: conventional format (`feat:`, `fix:`, `test:`) — no "Co-Authored-By"
- RTK prefix for all shell commands: `rtk git status`, `rtk git commit`, etc.
- All backend test commands: `cd backend && uv run pytest src/tests/<file> -v`
- All frontend build checks: `cd frontend && pnpm build`

---

## File Map

### Backend — files modified/created
| File | Action | Responsibility |
|---|---|---|
| `backend/src/infrastructure/ai/schemas.py` | Modify | Add `RfcFields`, register in `SCHEMA_REGISTRY` |
| `backend/src/domain/scoring/factors.py` | Modify | Fix `fecha_emision` reads from `fields` dict; parse ISO string |
| `backend/src/api/routers/documentos.py` | Modify | Extraction fail → needs_review; fix extract route; add DELETE |
| `backend/src/api/routers/admin.py` | Modify | Add `POST /demo/seed` endpoint |
| `backend/src/tests/test_ai_schemas.py` | Modify | Add: `"rfc"` in SCHEMA_REGISTRY |
| `backend/src/tests/test_scoring_factors_completitud.py` | Modify | Add: fecha_emision from fields, doc_expired fires, csf_stale fires |
| `backend/src/tests/test_scoring_factors_discrepancias.py` | Create | Full branch coverage for `factores_discrepancias` |
| `backend/src/tests/test_documentos_router.py` | Modify | Add: rfc upload OK, extraction fail → 200 + pending, DELETE doc |
| `backend/scripts/generate_demo_pdfs.py` | Modify | Add RFC content to `rfc.pdf` generator |

### Frontend — files modified/created
| File | Action | Responsibility |
|---|---|---|
| `frontend/lib/api-client.ts` | Modify | `UploadDocumentoResult` + `needs_review`; add `deleteDocumento`, `seedDemo` |
| `frontend/components/ScoreGauge.tsx` | Modify | Remove `/ 100` cap label; use threshold legend |
| `frontend/components/DocumentUploader.tsx` | Modify | Handle `needs_review: true` → redirect to revisar with toast |
| `frontend/components/FactorDetailCard.tsx` | Modify | Render `evidence` dict in human-readable plain language |
| `frontend/components/ActionCard.tsx` | Modify | Remove blocked SAT links; add contextual nav `Link` buttons |
| `frontend/app/page.tsx` | Modify | Add demo seed button (empty state + header) |
| `frontend/app/expedientes/[id]/page.tsx` | Modify | Convert to SWR client component; add delete + inline edit |
| `frontend/app/expedientes/[id]/reporte/page.tsx` | Modify | Add SWR for evaluation; remove `router.refresh()` |
| `frontend/hooks/use-expediente.ts` | Create | `useExpediente(id)` + `useDocumentos(id)` SWR hooks |

---

## BACKEND TASKS (Tasks 1–8)

---

### Task 1: Add `RfcFields` to SCHEMA_REGISTRY

**Files:**
- Modify: `backend/src/infrastructure/ai/schemas.py`
- Modify: `backend/src/tests/test_ai_schemas.py`

**Interfaces:**
- Produces: `SCHEMA_REGISTRY["rfc"]` → `RfcFields` (consumed by `upload_documento`, `extraer_campos`, and `factores_completitud`)

- [ ] **Step 1: Read existing schemas file to understand pattern**

```bash
cd backend && uv run python -c "from src.infrastructure.ai.schemas import SCHEMA_REGISTRY; print(sorted(SCHEMA_REGISTRY.keys()))"
```
Expected output: list without "rfc"

- [ ] **Step 2: Write failing test**

In `backend/src/tests/test_ai_schemas.py`, add:
```python
def test_rfc_in_schema_registry():
    from infrastructure.ai.schemas import SCHEMA_REGISTRY
    assert "rfc" in SCHEMA_REGISTRY

def test_rfc_fields_structure():
    from infrastructure.ai.schemas import SCHEMA_REGISTRY, RfcFields
    schema = SCHEMA_REGISTRY["rfc"]
    assert schema is RfcFields
    instance = RfcFields(rfc="EKU9003173C9", razon_social="Test SA de CV", domicilio_fiscal="Calle 1")
    assert instance.rfc == "EKU9003173C9"
    assert instance.razon_social == "Test SA de CV"
    assert instance.domicilio_fiscal == "Calle 1"

def test_rfc_fields_all_optional():
    from infrastructure.ai.schemas import RfcFields
    instance = RfcFields()
    assert instance.rfc is None
    assert instance.razon_social is None
    assert instance.domicilio_fiscal is None
```

- [ ] **Step 3: Run — confirm fail**

```bash
cd backend && uv run pytest src/tests/test_ai_schemas.py::test_rfc_in_schema_registry -v
```
Expected: `FAILED` — `AssertionError: assert 'rfc' in ...`

- [ ] **Step 4: Implement — add `RfcFields` and register it**

In `backend/src/infrastructure/ai/schemas.py`, add after `ManifestacionProtestaFields`:
```python
class RfcFields(BaseModel):
    rfc: str | None = None
    razon_social: str | None = None
    domicilio_fiscal: str | None = None
```

In `SCHEMA_REGISTRY`, add:
```python
    "rfc": RfcFields,
```

- [ ] **Step 5: Run — confirm pass**

```bash
cd backend && uv run pytest src/tests/test_ai_schemas.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd backend
rtk git add src/infrastructure/ai/schemas.py src/tests/test_ai_schemas.py
rtk git commit -m "feat: add RfcFields to SCHEMA_REGISTRY — fixes CORS 422 on rfc.pdf upload"
```

---

### Task 2: Fix `fecha_emision` reads wrong dict level in `factores_completitud`

**Files:**
- Modify: `backend/src/domain/scoring/factors.py`
- Modify: `backend/src/tests/test_scoring_factors_completitud.py`

**Interfaces:**
- Consumes: `doc["fields"]["fecha_emision"]` (ISO 8601 string like `"2026-03-01"`)
- Produces: `doc_expired` and `csf_stale` factors now fire correctly

- [ ] **Step 1: Write failing tests**

In `backend/src/tests/test_scoring_factors_completitud.py`, add:
```python
from datetime import date

def _make_doc(doc_type, fields=None, status="human_reviewed"):
    return {
        "id": "test-id",
        "doc_type": doc_type,
        "extraction_status": status,
        "fields": fields or {},
    }

def test_doc_expired_fires_when_fecha_in_fields():
    """comprobante_domicilio with fecha_emision > 90 days ago in fields should fire doc_expired."""
    from domain.scoring.factors import factores_completitud
    # All 8 docs present, so no doc_missing factors
    all_doc_types = [
        "acta_constitutiva", "identificacion_rep_legal", "poder_notarial",
        "encargo_conferido", "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
    ]
    docs = [_make_doc(t) for t in all_doc_types if t != "comprobante_domicilio"]
    old_date = "2025-01-01"  # > 90 days ago from any 2026 test date
    docs.append(_make_doc("comprobante_domicilio", {"fecha_emision": old_date}))
    hoy = date(2026, 6, 29)
    factores = factores_completitud(docs, [], hoy)
    codes = [f.factor_code for f in factores]
    assert "doc_expired" in codes, f"Expected doc_expired in {codes}"

def test_doc_expired_does_not_fire_for_recent_comprobante():
    from domain.scoring.factors import factores_completitud
    all_doc_types = [
        "acta_constitutiva", "identificacion_rep_legal", "poder_notarial",
        "encargo_conferido", "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
    ]
    docs = [_make_doc(t) for t in all_doc_types if t != "comprobante_domicilio"]
    docs.append(_make_doc("comprobante_domicilio", {"fecha_emision": "2026-06-01"}))
    hoy = date(2026, 6, 29)
    factores = factores_completitud(docs, [], hoy)
    codes = [f.factor_code for f in factores]
    assert "doc_expired" not in codes

def test_csf_stale_fires_when_fecha_in_fields():
    """CSF with fecha_emision from last month should fire csf_stale."""
    from domain.scoring.factors import factores_completitud
    all_doc_types = [
        "acta_constitutiva", "identificacion_rep_legal", "poder_notarial",
        "encargo_conferido", "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
    ]
    docs = [_make_doc(t) for t in all_doc_types if t != "csf"]
    docs.append(_make_doc("csf", {"fecha_emision": "2026-05-01"}))  # last month
    hoy = date(2026, 6, 29)
    factores = factores_completitud(docs, [], hoy)
    codes = [f.factor_code for f in factores]
    assert "csf_stale" in codes, f"Expected csf_stale in {codes}"

def test_csf_stale_does_not_fire_for_current_month():
    from domain.scoring.factors import factores_completitud
    all_doc_types = [
        "acta_constitutiva", "identificacion_rep_legal", "poder_notarial",
        "encargo_conferido", "comprobante_domicilio", "rfc", "csf", "manifestacion_protesta",
    ]
    docs = [_make_doc(t) for t in all_doc_types if t != "csf"]
    docs.append(_make_doc("csf", {"fecha_emision": "2026-06-01"}))  # current month
    hoy = date(2026, 6, 29)
    factores = factores_completitud(docs, [], hoy)
    codes = [f.factor_code for f in factores]
    assert "csf_stale" not in codes
```

- [ ] **Step 2: Run — confirm fail**

```bash
cd backend && uv run pytest src/tests/test_scoring_factors_completitud.py::test_doc_expired_fires_when_fecha_in_fields -v
```
Expected: `FAILED`

- [ ] **Step 3: Fix `factores_completitud` in `factors.py`**

Replace lines 55–67 of `backend/src/domain/scoring/factors.py` (the inner loop body):

```python
    for doc in documentos:
        if doc["extraction_status"] != "human_reviewed":
            continue
        fields = doc.get("fields") or {}
        if any(v in (None, "") for v in fields.values()):
            factores.append(Factor("doc_data_incomplete", 15, False, f"El documento {doc['doc_type']} no aportó todos los campos obligatorios.", evidence={"documento_id": doc["id"]}))

        fecha_str = fields.get("fecha_emision")
        fecha = None
        if fecha_str:
            try:
                from datetime import date as _date
                fecha = _date.fromisoformat(str(fecha_str))
            except (ValueError, TypeError):
                fecha = None

        if doc["doc_type"] == "comprobante_domicilio" and fecha:
            dias = (hoy - fecha).days
            if dias > VIGENCIA_DIAS["comprobante_domicilio"]:
                factores.append(Factor("doc_expired", 20, False, f"Comprobante de domicilio con {dias} días de antigüedad (límite: 90 días).", evidence={"documento_id": doc["id"], "dias_antiguedad": dias}))
        if doc["doc_type"] == "csf" and fecha:
            if (fecha.year, fecha.month) != (hoy.year, hoy.month):
                factores.append(Factor("csf_stale", 25, False, f"La CSF es del {fecha.strftime('%B %Y')} — se requiere del mes en curso ({hoy.strftime('%B %Y')}).", evidence={"documento_id": doc["id"], "fecha_csf": str(fecha)}))
        if doc["doc_type"] == "manifestacion_protesta" and not fields.get("declara_no_69b_49bis"):
            factores.append(Factor("manifestacion_incompleta", 20, False, "La Manifestación bajo Protesta no confirma la cláusula de los Art. 69-B / 49 Bis CFF."))
```

- [ ] **Step 4: Run all completitud tests**

```bash
cd backend && uv run pytest src/tests/test_scoring_factors_completitud.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd backend
rtk git add src/domain/scoring/factors.py src/tests/test_scoring_factors_completitud.py
rtk git commit -m "fix: read fecha_emision from doc fields dict — doc_expired and csf_stale now fire correctly"
```

---

### Task 3: Add full TDD coverage for `factores_discrepancias`

**Files:**
- Create: `backend/src/tests/test_scoring_factors_discrepancias.py`

**Interfaces:**
- Consumes: `factores_discrepancias(resultado)` where `resultado` is an object with bool flags

- [ ] **Step 1: Create test file**

```python
# backend/src/tests/test_scoring_factors_discrepancias.py
"""TDD coverage for factores_discrepancias — previously had zero tests."""
from types import SimpleNamespace
import pytest
from domain.scoring.factors import factores_discrepancias


def _resultado(**flags):
    defaults = dict(
        rfc_discrepante=False,
        razon_social_discrepante=False,
        domicilio_discrepante=False,
        representante_discrepante=False,
        fechas_inconsistentes=False,
    )
    defaults.update(flags)
    return SimpleNamespace(**defaults)


def test_all_clean_returns_empty():
    factores = factores_discrepancias(_resultado())
    assert factores == []


def test_rfc_discrepante_adds_disc_rfc():
    factores = factores_discrepancias(_resultado(rfc_discrepante=True))
    codes = [f.factor_code for f in factores]
    assert codes == ["disc_rfc"]
    assert factores[0].points == 50


def test_razon_social_discrepante_adds_factor():
    factores = factores_discrepancias(_resultado(razon_social_discrepante=True))
    codes = [f.factor_code for f in factores]
    assert "disc_razon_social" in codes
    pts = {f.factor_code: f.points for f in factores}
    assert pts["disc_razon_social"] == 30


def test_domicilio_discrepante_adds_factor():
    factores = factores_discrepancias(_resultado(domicilio_discrepante=True))
    codes = [f.factor_code for f in factores]
    assert "disc_domicilio" in codes
    assert {f.factor_code: f.points for f in factores}["disc_domicilio"] == 20


def test_representante_discrepante_adds_factor():
    factores = factores_discrepancias(_resultado(representante_discrepante=True))
    codes = [f.factor_code for f in factores]
    assert "disc_representante" in codes
    assert {f.factor_code: f.points for f in factores}["disc_representante"] == 25


def test_fechas_inconsistentes_adds_factor():
    factores = factores_discrepancias(_resultado(fechas_inconsistentes=True))
    codes = [f.factor_code for f in factores]
    assert "disc_fechas" in codes
    assert {f.factor_code: f.points for f in factores}["disc_fechas"] == 15


def test_all_flags_true_returns_five_factors():
    factores = factores_discrepancias(_resultado(
        rfc_discrepante=True,
        razon_social_discrepante=True,
        domicilio_discrepante=True,
        representante_discrepante=True,
        fechas_inconsistentes=True,
    ))
    assert len(factores) == 5
    total = sum(f.points for f in factores)
    assert total == 50 + 30 + 20 + 25 + 15  # 140 pts


def test_none_are_critical_blocks():
    factores = factores_discrepancias(_resultado(
        rfc_discrepante=True, razon_social_discrepante=True,
    ))
    assert all(not f.is_critical_block for f in factores)
```

- [ ] **Step 2: Run — confirm all pass (this is existing code with new tests)**

```bash
cd backend && uv run pytest src/tests/test_scoring_factors_discrepancias.py -v
```
Expected: all PASS (the function is correct; we're adding missing test coverage)

- [ ] **Step 3: Commit**

```bash
cd backend
rtk git add src/tests/test_scoring_factors_discrepancias.py
rtk git commit -m "test: add full coverage for factores_discrepancias — was untested"
```

---

### Task 4: Fix upload extraction failure → option B (needs_review response)

**Files:**
- Modify: `backend/src/api/routers/documentos.py`
- Modify: `backend/src/tests/test_documentos_router.py`

**Interfaces:**
- Produces: `POST /documentos/upload` returns `{"documento_id": str, "doc_type": str, "fields": dict, "extraction_status": str, "needs_review": bool}`

- [ ] **Step 1: Read existing upload tests to understand test client pattern**

```bash
cd backend && uv run pytest src/tests/test_documentos_router.py -v --collect-only 2>&1 | head -40
```

- [ ] **Step 2: Write failing tests**

In `backend/src/tests/test_documentos_router.py`, add the following tests (add at the bottom of the file):

```python
def test_upload_rfc_doc_type_succeeds(client, fake_supabase):
    """rfc is now a valid doc_type — upload should not 422."""
    import io
    # Minimal valid PDF bytes (just enough to not crash pdfplumber)
    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    exp_id = fake_supabase.make_expediente_id()
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": exp_id, "doc_type": "rfc"},
        files={"file": ("rfc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    # Should be 200, not 422
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "documento_id" in body
    assert "needs_review" in body


def test_upload_extraction_failure_returns_pending_with_needs_review(client, fake_supabase, monkeypatch):
    """When extraer_campos raises, upload returns 200 with needs_review=True."""
    import io
    from api.routers import documentos as doc_router

    def failing_extractor(*args, **kwargs):
        raise RuntimeError("Groq unavailable")

    monkeypatch.setattr(doc_router, "extraer_campos", failing_extractor)

    pdf_bytes = b"%PDF-1.4\n%%EOF"
    exp_id = fake_supabase.make_expediente_id()
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": exp_id, "doc_type": "csf"},
        files={"file": ("csf.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["extraction_status"] == "pending"
    assert body["needs_review"] is True


def test_upload_success_returns_needs_review_false(client, fake_supabase, monkeypatch):
    """Successful extraction returns needs_review=False."""
    import io
    from api.routers import documentos as doc_router

    def mock_extractor(supabase, doc_type, texto):
        return {"rfc": "EKU9003173C9", "razon_social": "Test SA de CV"}

    monkeypatch.setattr(doc_router, "extraer_campos", mock_extractor)
    # Also mock extraer_texto_de_bytes to return something
    monkeypatch.setattr(doc_router, "extraer_texto_de_bytes", lambda b: "RFC: EKU9003173C9")

    pdf_bytes = b"%PDF-1.4\n%%EOF"
    exp_id = fake_supabase.make_expediente_id()
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": exp_id, "doc_type": "csf"},
        files={"file": ("csf.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is False
    assert body["extraction_status"] == "extracted"
```

- [ ] **Step 3: Run — confirm fail**

```bash
cd backend && uv run pytest src/tests/test_documentos_router.py::test_upload_rfc_doc_type_succeeds -v
```
Expected: `FAILED` with 422

- [ ] **Step 4: Update `upload_documento` in `documentos.py`**

Replace the extraction section (lines ~115-131) in `backend/src/api/routers/documentos.py`:

```python
    texto = extraer_texto_de_bytes(content)

    needs_review = False
    campos: dict = {}
    if texto.strip():
        try:
            campos = extraer_campos(supabase, doc_type, texto)
        except Exception:
            needs_review = True

    if not campos:
        needs_review = True

    extraction_status = "extracted" if campos and not needs_review else "pending"

    documento_id = str(uuid.uuid4())
    supabase.table("documentos").insert(
        {
            "id": documento_id,
            "expediente_id": expediente_id,
            "doc_type": doc_type,
            "entry_method": "uploaded",
            "storage_path": storage_path,
            "extracted_raw": campos,
            "fields": campos,
            "extraction_status": extraction_status,
        }
    ).execute()

    return {
        "documento_id": documento_id,
        "doc_type": doc_type,
        "fields": campos,
        "extraction_status": extraction_status,
        "needs_review": needs_review,
    }
```

- [ ] **Step 5: Run all upload tests**

```bash
cd backend && uv run pytest src/tests/test_documentos_router.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd backend
rtk git add src/api/routers/documentos.py src/tests/test_documentos_router.py
rtk git commit -m "fix: upload extraction failure returns 200+pending+needs_review — option B"
```

---

### Task 5: Fix `extract_documento` route — use Storage bytes not local path

**Files:**
- Modify: `backend/src/api/routers/documentos.py`
- Modify: `backend/src/tests/test_documentos_router.py`

**Interfaces:**
- Consumes: `supabase.storage.from_("kyb-docs").download(storage_path)` → bytes
- Produces: working text extraction on Vercel (no local filesystem access)

- [ ] **Step 1: Write failing test**

In `backend/src/tests/test_documentos_router.py`, add:

```python
def test_extract_documento_uses_storage_not_local_path(client, fake_supabase, monkeypatch):
    """extract_documento must download from Storage, not try to open a local file."""
    from api.routers import documentos as doc_router

    downloaded = []

    def mock_download(path):
        downloaded.append(path)
        return b"%PDF-1.4\n%%EOF"

    # Patch storage download on fake_supabase
    monkeypatch.setattr(fake_supabase.storage.from_("kyb-docs"), "download", mock_download)
    monkeypatch.setattr(doc_router, "extraer_texto_de_bytes", lambda b: "RFC: EKU9003173C9")
    monkeypatch.setattr(doc_router, "extraer_campos", lambda *a, **kw: {"rfc": "EKU9003173C9"})

    # First create a doc record in fake_supabase
    doc_id = "test-doc-id-extract"
    fake_supabase.table("documentos").insert({
        "id": doc_id, "expediente_id": "exp-1", "doc_type": "csf",
        "storage_path": "exp-1/csf.pdf", "extraction_status": "pending",
        "entry_method": "uploaded", "fields": {},
    }).execute()

    resp = client.post(f"/documentos/{doc_id}/extract")
    assert resp.status_code == 200
    assert len(downloaded) == 1, "Storage download should have been called"
    assert downloaded[0] == "exp-1/csf.pdf"
```

- [ ] **Step 2: Run — confirm fail**

```bash
cd backend && uv run pytest src/tests/test_documentos_router.py::test_extract_documento_uses_storage_not_local_path -v
```

- [ ] **Step 3: Fix `extract_documento` in `documentos.py`**

Replace the route handler body for `POST /{documento_id}/extract`:

```python
@router.post("/{documento_id}/extract")
def extract_documento(documento_id: str, supabase=Depends(get_supabase_client)):
    result = supabase.table("documentos").select("*").eq("id", documento_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    doc = result.data[0]
    storage_path = doc.get("storage_path")
    if not storage_path:
        raise HTTPException(status_code=422, detail="El documento no tiene archivo en Storage")
    try:
        content = supabase.storage.from_("kyb-docs").download(storage_path)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo descargar el archivo de Storage: {e}")
    texto = extraer_texto_de_bytes(content)
    needs_review = False
    campos: dict = {}
    if texto.strip():
        try:
            campos = extraer_campos(supabase, doc["doc_type"], texto)
        except Exception:
            needs_review = True
    if not campos:
        needs_review = True
    extraction_status = "extracted" if campos and not needs_review else "pending"
    supabase.table("documentos").update(
        {"extracted_raw": campos, "fields": campos, "extraction_status": extraction_status}
    ).eq("id", documento_id).execute()
    return {"extraction_status": extraction_status, "fields": campos, "needs_review": needs_review}
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest src/tests/test_documentos_router.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd backend
rtk git add src/api/routers/documentos.py src/tests/test_documentos_router.py
rtk git commit -m "fix: extract_documento downloads from Supabase Storage instead of local filesystem"
```

---

### Task 6: Add `DELETE /documentos/{id}` endpoint

**Files:**
- Modify: `backend/src/api/routers/documentos.py`
- Modify: `backend/src/tests/test_documentos_router.py`

**Interfaces:**
- Produces: `DELETE /documentos/{documento_id}` → HTTP 204 (also deletes from Storage)

- [ ] **Step 1: Write failing test**

```python
def test_delete_documento_returns_204(client, fake_supabase):
    """DELETE /documentos/{id} removes the doc record and returns 204."""
    # Create a doc to delete
    doc_id = "doc-to-delete"
    fake_supabase.table("documentos").insert({
        "id": doc_id, "expediente_id": "exp-del", "doc_type": "rfc",
        "storage_path": "exp-del/rfc.pdf", "extraction_status": "pending",
        "entry_method": "uploaded", "fields": {},
    }).execute()

    resp = client.delete(f"/documentos/{doc_id}")
    assert resp.status_code == 204

    # Verify deleted
    rows = fake_supabase.table("documentos").select("id").eq("id", doc_id).execute().data
    assert rows == []


def test_delete_documento_404_if_not_found(client, fake_supabase):
    resp = client.delete("/documentos/nonexistent-id")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run — confirm fail**

```bash
cd backend && uv run pytest src/tests/test_documentos_router.py::test_delete_documento_returns_204 -v
```

- [ ] **Step 3: Add DELETE endpoint to `documentos.py`**

Add after the `revisar_documento` PATCH route:

```python
@router.delete("/{documento_id}", status_code=204)
def eliminar_documento(documento_id: str, supabase=Depends(get_supabase_client)):
    result = supabase.table("documentos").select("id, storage_path").eq("id", documento_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    storage_path = result.data[0].get("storage_path")
    if storage_path:
        try:
            supabase.storage.from_("kyb-docs").remove([storage_path])
        except Exception:
            pass  # Storage delete is best-effort; DB delete always happens
    supabase.table("documentos").delete().eq("id", documento_id).execute()
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest src/tests/test_documentos_router.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd backend
rtk git add src/api/routers/documentos.py src/tests/test_documentos_router.py
rtk git commit -m "feat: add DELETE /documentos/{id} endpoint with Storage cleanup"
```

---

### Task 7: Add `POST /demo/seed` endpoint

**Files:**
- Modify: `backend/src/api/routers/admin.py`
- Create: `backend/src/tests/test_demo_seed.py`

**Interfaces:**
- Produces: `POST /demo/seed` → `{"expediente_ids": [str, str, str], "evaluations": [{id, decision, score_total}], "message": str}`

- [ ] **Step 1: Write failing test**

Create `backend/src/tests/test_demo_seed.py`:

```python
"""TDD for POST /demo/seed endpoint."""
import pytest


def test_demo_seed_creates_three_expedientes(client, fake_supabase):
    """POST /demo/seed creates exactly 3 demo expedientes."""
    resp = client.post("/admin/demo/seed")
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "expediente_ids" in body
    assert len(body["expediente_ids"]) == 3
    assert "message" in body


def test_demo_seed_is_idempotent(client, fake_supabase):
    """Calling seed twice cleans and re-creates — same 3 RFCs."""
    client.post("/admin/demo/seed")
    resp2 = client.post("/admin/demo/seed")
    assert resp2.status_code == 200
    # Should still be exactly 3 (not 6)
    all_exp = fake_supabase.table("expedientes").select("rfc").execute().data
    demo_rfcs = {r["rfc"] for r in all_exp if r["rfc"] in ("EKU9003173C9", "COX010101AB1", "AAA120730823")}
    assert len(demo_rfcs) == 3


def test_demo_seed_returns_evaluations(client, fake_supabase, monkeypatch):
    """Each seeded expediente gets evaluated and returns decision."""
    from services import evaluation_service, reconciliation_service

    def fake_recon(supabase, exp_id):
        from types import SimpleNamespace
        return SimpleNamespace(
            rfc_discrepante=False, razon_social_discrepante=False,
            domicilio_discrepante=False, representante_discrepante=False,
            fechas_inconsistentes=False,
        )

    def fake_eval(supabase, exp_id, recon, hoy=None):
        return {"score_total": 0, "decision": "safe", "factores_score": {},
                "factores_detail": [], "acciones_sugeridas": [], "needs_update": False}

    monkeypatch.setattr(reconciliation_service, "reconciliar_expediente", fake_recon)
    monkeypatch.setattr(evaluation_service, "evaluar_expediente", fake_eval)

    resp = client.post("/admin/demo/seed")
    assert resp.status_code == 200
    body = resp.json()
    assert "evaluations" in body
    assert len(body["evaluations"]) == 3
```

- [ ] **Step 2: Run — confirm fail**

```bash
cd backend && uv run pytest src/tests/test_demo_seed.py::test_demo_seed_creates_three_expedientes -v
```

- [ ] **Step 3: Add seed endpoint to `admin.py`**

Add to `backend/src/api/routers/admin.py`:

```python
import uuid as _uuid
from datetime import date as _date

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
```

- [ ] **Step 4: Run all tests**

```bash
cd backend && uv run pytest src/tests/ -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd backend
rtk git add src/api/routers/admin.py src/tests/test_demo_seed.py
rtk git commit -m "feat: add POST /admin/demo/seed — idempotent demo data loader with evaluations"
```

---

### Task 8: Regenerate `rfc.pdf` with correct field content

**Files:**
- Modify: `backend/scripts/generate_demo_pdfs.py`
- Regenerate: `backend/scripts/demo_pdfs/escenario_*/rfc.pdf`

**Interfaces:**
- Produces: `rfc.pdf` files with extractable text matching `RfcFields` schema

- [ ] **Step 1: Find and update the rfc.pdf generator section**

Read `backend/scripts/generate_demo_pdfs.py` and find the section that generates `rfc.pdf`. Update it so the content matches the `RfcFields` schema (rfc, razon_social, domicilio_fiscal). The exact content per scenario:

**Scenario 1 (escenario_1_limpio):**
```
CÉDULA DE IDENTIFICACIÓN FISCAL

RFC: EKU9003173C9
Razón Social: Escuela Kemper Urgate SA de CV
Domicilio Fiscal: Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700

Régimen Fiscal: 601 - General de Ley Personas Morales
```

**Scenario 2 (escenario_2_discrepancia):**
```
CÉDULA DE IDENTIFICACIÓN FISCAL

RFC: COX010101AB1
Razón Social: Corporativo X SA de CV
Domicilio Fiscal: Avenida Insurgentes Sur Num 123, Colonia Roma

Régimen Fiscal: 601 - General de Ley Personas Morales
```

**Scenario 3 (escenario_3_alto_riesgo):**
```
CÉDULA DE IDENTIFICACIÓN FISCAL

RFC: AAA120730823
Razón Social: Empresa en Lista Negra SA de CV
Domicilio Fiscal: Calle Reforma 456, Col. Centro, CDMX, CP 06000

Régimen Fiscal: 601 - General de Ley Personas Morales
```

- [ ] **Step 2: Re-run the generator**

```bash
cd backend && uv run python scripts/generate_demo_pdfs.py
```

- [ ] **Step 3: Verify text extraction from the new rfc.pdf files**

```bash
cd backend && uv run python -c "
from src.infrastructure.ai.pdf import extraer_texto_de_bytes
for scenario in ['escenario_1_limpio', 'escenario_2_discrepancia', 'escenario_3_alto_riesgo']:
    with open(f'scripts/demo_pdfs/{scenario}/rfc.pdf', 'rb') as f:
        texto = extraer_texto_de_bytes(f.read())
    print(f'{scenario}:', repr(texto[:120]))
    assert 'RFC:' in texto, f'Missing RFC: in {scenario}'
"
```
Expected: each prints text containing "RFC:" and the correct RFC value

- [ ] **Step 4: Commit**

```bash
cd backend
rtk git add scripts/generate_demo_pdfs.py scripts/demo_pdfs/
rtk git commit -m "fix: regenerate rfc.pdf with RfcFields content — extractable by Groq"
```

---

## FRONTEND TASKS (Tasks 9–16)

---

### Task 9: Update `api-client.ts` — new types and methods

**Files:**
- Modify: `frontend/lib/api-client.ts`

**Interfaces:**
- Produces: `UploadDocumentoResult.needs_review: boolean`, `api.deleteDocumento(id)`, `api.seedDemo()`

- [ ] **Step 1: Update `UploadDocumentoResult` and add new methods**

In `frontend/lib/api-client.ts`:

1. Update `UploadDocumentoResult`:
```typescript
export type UploadDocumentoResult = {
  documento_id: string;
  extraction_status: string;
  needs_review: boolean;
  fields?: Record<string, unknown>;
};
```

2. Add to the `api` object:
```typescript
  deleteDocumento: (id: string): Promise<void> =>
    request(`/documentos/${id}`, { method: "DELETE" }),

  seedDemo: (): Promise<{ expediente_ids: string[]; evaluations: unknown[]; message: string }> =>
    request("/admin/demo/seed", { method: "POST" }),
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm exec tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd frontend
rtk git add lib/api-client.ts
rtk git commit -m "feat: extend api-client — needs_review, deleteDocumento, seedDemo"
```

---

### Task 10: Create `useExpediente` and `useDocumentos` SWR hooks

**Files:**
- Create: `frontend/hooks/use-expediente.ts`

**Interfaces:**
- Produces: `useExpediente(id)` → `{expediente, isLoading, mutate}`, `useDocumentos(id)` → `{documentos, isLoading, mutate}`

- [ ] **Step 1: Create hook file**

```typescript
// frontend/hooks/use-expediente.ts
"use client";
import useSWR from "swr";
import { api } from "@/lib/api-client";
import type { Expediente, Documento } from "@/lib/api-client";

export function useExpediente(id: string) {
  const { data, isLoading, mutate, error } = useSWR<Expediente>(
    id ? `expediente-${id}` : null,
    () => api.getExpediente(id),
    { revalidateOnFocus: true }
  );
  return { expediente: data ?? null, isLoading, mutate, error };
}

export function useDocumentos(expedienteId: string) {
  const { data, isLoading, mutate, error } = useSWR<Documento[]>(
    expedienteId ? `documentos-${expedienteId}` : null,
    () => api.listDocumentos(expedienteId),
    { revalidateOnFocus: true }
  );
  return { documentos: data ?? [], isLoading, mutate, error };
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && pnpm exec tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
cd frontend
rtk git add hooks/use-expediente.ts
rtk git commit -m "feat: add useExpediente and useDocumentos SWR hooks"
```

---

### Task 11: Fix `ScoreGauge` — remove misleading "/ 100" cap

**Files:**
- Modify: `frontend/components/ScoreGauge.tsx`

**Interfaces:**
- Consumes: `score: number` (can exceed 100 when multiple factors fire), `decision: string`
- Produces: clear threshold legend without implying 100-point ceiling

- [ ] **Step 1: Replace score label and bottom legend**

In `frontend/components/ScoreGauge.tsx`, replace:

```tsx
          <p className={`text-5xl font-bold leading-none ${config.textClass}`}>
            {score}
            <span className="text-lg font-normal text-muted-foreground ml-1">/ 100</span>
          </p>
```

with:

```tsx
          <p className={`text-5xl font-bold leading-none ${config.textClass}`}>
            {score}
            <span className="text-sm font-normal text-muted-foreground ml-1">pts de riesgo</span>
          </p>
```

And replace the bottom row:

```tsx
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>0 — Sin riesgo</span>
        <span>30 — Revisión</span>
        <span>70+ — Alto riesgo</span>
      </div>
```

with:

```tsx
      <div className="flex justify-between text-xs text-muted-foreground">
        <span className="text-success">0–29 aprobado</span>
        <span className="text-warning">30–69 revisión</span>
        <span className="text-destructive">70+ bloqueado</span>
      </div>
```

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && pnpm exec tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
cd frontend
rtk git add components/ScoreGauge.tsx
rtk git commit -m "fix: ScoreGauge removes misleading /100 cap — shows pts de riesgo with threshold legend"
```

---

### Task 12: `DocumentUploader` — handle `needs_review: true` (option B)

**Files:**
- Modify: `frontend/components/DocumentUploader.tsx`

**Interfaces:**
- Consumes: `UploadDocumentoResult.needs_review: boolean`
- Produces: when `needs_review=true`, redirect to `/expedientes/{id}/revisar?documento_id={doc_id}` with Sonner toast

- [ ] **Step 1: Update `subirArchivo` function**

In `frontend/components/DocumentUploader.tsx`, update the `subirArchivo` function:

```typescript
  async function subirArchivo(file: File) {
    setEstado("uploading");
    setErrorMsg(null);
    setPasoActual(0);
    try {
      const result = await api.uploadDocumento(expedienteId, docType, file);
      setDocId(result.documento_id);
      setPasoActual(3);
      if (result.needs_review) {
        toast("La IA no pudo extraer campos — completá los datos manualmente", {
          description: "Serás redirigido a la pantalla de revisión.",
        });
        setTimeout(() => {
          window.location.href = `/expedientes/${expedienteId}/revisar?documento_id=${result.documento_id}`;
        }, 1200);
        setEstado("done");
        return;
      }
      setEstado("done");
      onDone?.();
      router.refresh();
    } catch (err) {
      if (err instanceof DuplicateDocumentoError && err.documentoId) {
        setDocId(err.documentoId);
        setEstado("done");
        onDone?.();
      } else {
        setErrorMsg(err instanceof Error ? err.message : "Error al procesar");
        setEstado("error");
      }
    }
  }
```

Add import at top if not present: `import { toast } from "sonner";`

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && pnpm exec tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
cd frontend
rtk git add components/DocumentUploader.tsx
rtk git commit -m "feat: DocumentUploader redirects to revisar when AI extraction fails (option B)"
```

---

### Task 13: Expediente detail page — SWR + delete document + inline edit

**Files:**
- Modify: `frontend/app/expedientes/[id]/page.tsx`

This is the largest frontend task. Read the file first with codegraph_explore before editing.

**Interfaces:**
- Consumes: `useExpediente(id)`, `useDocumentos(id)` from Task 10
- Consumes: `api.deleteDocumento(id)`, `api.updateExpediente(id, data)` from Task 9
- Produces: real-time doc list; delete button per doc card; pencil edit on expediente header

- [ ] **Step 1: Read current page structure**

```bash
cd frontend && cat app/expedientes/[id]/page.tsx | head -80
```

- [ ] **Step 2: Convert to client component with SWR**

At the top of `frontend/app/expedientes/[id]/page.tsx`, ensure:
```typescript
"use client";
```

Replace server-side data fetching with SWR hooks:
```typescript
import { useExpediente, useDocumentos } from "@/hooks/use-expediente";

// Inside the component:
const { expediente, mutate: mutateExpediente } = useExpediente(id);
const { documentos, mutate: mutateDocumentos } = useDocumentos(id);
```

- [ ] **Step 3: Add delete document flow**

Add a `handleDeleteDocumento` function to the component:
```typescript
const [deletingId, setDeletingId] = useState<string | null>(null);

async function handleDeleteDocumento(docId: string) {
  setDeletingId(docId);
  try {
    await api.deleteDocumento(docId);
    toast.success("Documento eliminado");
    await mutateDocumentos();
  } catch {
    toast.error("Error al eliminar documento");
  } finally {
    setDeletingId(null);
  }
}
```

On each document card, add a delete button:
```tsx
<button
  onClick={() => {
    if (confirm("¿Eliminar este documento? Esta acción no se puede deshacer.")) {
      handleDeleteDocumento(doc.id);
    }
  }}
  disabled={deletingId === doc.id}
  className="text-xs text-destructive hover:underline disabled:opacity-50"
>
  {deletingId === doc.id ? "Eliminando…" : "Eliminar"}
</button>
```

- [ ] **Step 4: Add inline edit dialog for expediente metadata**

Add edit state and handler:
```typescript
const [editOpen, setEditOpen] = useState(false);
const [editData, setEditData] = useState({ razon_social: "", rfc: "", domicilio_fiscal: "", representante_legal: "" });
const [saving, setSaving] = useState(false);

function openEdit() {
  if (!expediente) return;
  setEditData({
    razon_social: expediente.razon_social,
    rfc: expediente.rfc,
    domicilio_fiscal: expediente.domicilio_fiscal ?? "",
    representante_legal: expediente.representante_legal ?? "",
  });
  setEditOpen(true);
}

async function saveEdit() {
  setSaving(true);
  try {
    await api.updateExpediente(id, editData);
    toast.success("Expediente actualizado");
    await mutateExpediente();
    setEditOpen(false);
  } catch {
    toast.error("Error al actualizar");
  } finally {
    setSaving(false);
  }
}
```

In the expediente header, add a pencil button next to the razón social:
```tsx
<button onClick={openEdit} className="ml-2 text-muted-foreground hover:text-foreground" title="Editar datos">
  <Pencil className="size-4" />
</button>
```

Add a Dialog (from shadcn) that renders when `editOpen=true` with inputs for all 4 fields.

Import `Pencil` from `lucide-react` and `Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter` from `@/components/ui/dialog`.

- [ ] **Step 5: Replace router.refresh() with mutate calls**

Search for `router.refresh()` in the file. Replace each with:
```typescript
await mutateDocumentos();
await mutateExpediente();
```

- [ ] **Step 6: TypeScript + build check**

```bash
cd frontend && pnpm exec tsc --noEmit && pnpm build 2>&1 | tail -20
```

- [ ] **Step 7: Commit**

```bash
cd frontend
rtk git add app/expedientes/
rtk git commit -m "feat: detail page — SWR real-time, delete documents, inline expediente edit"
```

---

### Task 14: Report page — SWR + SAT date context + remove router.refresh()

**Files:**
- Modify: `frontend/app/expedientes/[id]/reporte/page.tsx`

**Interfaces:**
- Consumes: `useLatestEvaluation(id)` (create inline in this page or in use-expediente.ts)
- Produces: auto-refreshing evaluation data after EvaluateButton click

- [ ] **Step 1: Add `useLatestEvaluation` to hooks file**

In `frontend/hooks/use-expediente.ts`, add:
```typescript
import type { EvaluationResult } from "@/lib/api-client";

export function useLatestEvaluation(expedienteId: string) {
  const { data, isLoading, mutate, error } = useSWR<EvaluationResult | null>(
    expedienteId ? `evaluation-latest-${expedienteId}` : null,
    () => api.getLatestEvaluation(expedienteId),
    { revalidateOnFocus: true }
  );
  return { evaluation: data ?? null, isLoading, mutate, error };
}
```

- [ ] **Step 2: Convert report page to client component**

Add `"use client"` at top of `frontend/app/expedientes/[id]/reporte/page.tsx`.

Use `useLatestEvaluation` to get evaluation data. Replace any server-side fetching.

- [ ] **Step 3: Wire EvaluateButton to mutate instead of router.refresh()**

The `EvaluateButton` component (in `reporte/EvaluateButton.tsx`) currently calls `router.refresh()`. Update it to accept an `onEvaluated?: () => void` prop and call it after evaluation:

```typescript
// In EvaluateButton.tsx
export function EvaluateButton({ expedienteId, onEvaluated }: { expedienteId: string; onEvaluated?: () => void }) {
  // ...
  async function handleEvaluate() {
    setLoading(true);
    try {
      await api.evaluate(expedienteId);
      await revalidateExpedientes();
      toast.success("Evaluación completada");
      onEvaluated?.();  // ← replaces router.refresh()
    } catch (err) {
      // ...
    } finally {
      setLoading(false);
    }
  }
```

In the report page, pass `onEvaluated={() => mutateEvaluation()}`:
```tsx
<EvaluateButton expedienteId={id} onEvaluated={() => mutateEvaluation()} />
```

- [ ] **Step 4: TypeScript + build check**

```bash
cd frontend && pnpm exec tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
cd frontend
rtk git add app/expedientes/[id]/reporte/ hooks/use-expediente.ts
rtk git commit -m "feat: report page — SWR real-time evaluation, EvaluateButton uses mutate"
```

---

### Task 15: `FactorDetailCard` — render evidence in plain language

**Files:**
- Modify: `frontend/components/FactorDetailCard.tsx`

**Interfaces:**
- Consumes: `factor.evidence: Record<string, unknown> | null`
- Produces: human-readable "Dato detectado" section below legal ref

- [ ] **Step 1: Add evidence renderer**

In `frontend/components/FactorDetailCard.tsx`, after the existing `legal_ref` display, add an evidence section. First, add this helper function inside the component file (before the main component):

```typescript
function renderEvidence(evidence: Record<string, unknown> | null, docType?: string): string | null {
  if (!evidence || Object.keys(evidence).length === 0) return null;

  const parts: string[] = [];

  if (evidence.doc_type) {
    const label = DOC_TYPE_LABELS[evidence.doc_type as string] ?? String(evidence.doc_type);
    parts.push(`Documento afectado: ${label}`);
  }
  if (evidence.documento_id) {
    const shortId = String(evidence.documento_id).slice(0, 8);
    parts.push(`ID del documento: ${shortId}…`);
  }
  if (evidence.manual_review_required === true) {
    parts.push("No existe lista pública del SAT para este artículo — requiere revisión manual por el agente");
  }
  if (typeof evidence.dias_antiguedad === "number") {
    parts.push(`Antigüedad del documento: ${evidence.dias_antiguedad} días (límite: 90 días)`);
  }
  if (evidence.fecha_csf) {
    parts.push(`Fecha de la CSF en expediente: ${evidence.fecha_csf}`);
  }

  return parts.length > 0 ? parts.join(" · ") : null;
}
```

Then inside the `FactorDetailCard` component, add after the legal ref section:

```tsx
{factor.evidence && renderEvidence(factor.evidence) && (
  <div className="mt-2 rounded-md bg-muted/50 px-3 py-2">
    <p className="text-xs font-medium text-muted-foreground mb-0.5">Dato detectado</p>
    <p className="text-xs text-foreground/80">{renderEvidence(factor.evidence)}</p>
  </div>
)}
```

- [ ] **Step 2: TypeScript + build**

```bash
cd frontend && pnpm exec tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
cd frontend
rtk git add components/FactorDetailCard.tsx
rtk git commit -m "feat: FactorDetailCard shows evidence data in plain language"
```

---

### Task 16: `ActionCard` — remove blocked SAT links, add contextual navigation

**Files:**
- Modify: `frontend/components/ActionCard.tsx`
- Modify: `frontend/app/expedientes/[id]/reporte/page.tsx` (pass `expedienteId` to ActionCard)

**Interfaces:**
- Consumes: `expedienteId: string` (new prop on ActionCard)
- Produces: contextual navigation links instead of blocked external SAT URLs

- [ ] **Step 1: Update `ActionCard` Props and add nav links**

In `frontend/components/ActionCard.tsx`:

1. Update `Props` type:
```typescript
type Props = {
  accion: string;
  relatedFactor?: FactorDetail;
  index: number;
  expedienteId: string;
};
```

2. Remove the `verifyUrl`/`verifyLabel` fields from `DetailedAction` and from `FACTOR_ACTIONS`. Replace them with `navLabel` and `navHref` factory:

```typescript
function getNavLink(factorCode: string, expedienteId: string, evidence?: Record<string, unknown> | null): { href: string; label: string } | null {
  if (factorCode === "doc_missing" && evidence?.doc_type) {
    return { href: `/expedientes/${expedienteId}`, label: "Ir al expediente → cargar documento" };
  }
  if (factorCode.startsWith("disc_") || factorCode.startsWith("doc_")) {
    return { href: `/expedientes/${expedienteId}`, label: "Ir al expediente" };
  }
  if (factorCode === "csf_stale" || factorCode === "doc_expired") {
    return { href: `/expedientes/${expedienteId}`, label: "Ir al expediente → reemplazar documento" };
  }
  return null;
}
```

3. In the `ActionCard` JSX, replace the external `<a>` block with:
```tsx
{(() => {
  const nav = relatedFactor ? getNavLink(relatedFactor.factor_code, expedienteId, relatedFactor.evidence) : null;
  return nav ? (
    <div className="ml-9">
      <Link
        href={nav.href}
        className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
      >
        <ArrowRight className="size-3" />
        {nav.label}
      </Link>
    </div>
  ) : null;
})()}
```

Import `Link` from `next/link` and `ArrowRight` from `lucide-react`.

Remove import of `ExternalLink` if no longer used.

4. For `sat_*` factors, add an informational note instead of the external link:
```tsx
{relatedFactor?.category === "sat" && relatedFactor.factor_code !== "art_49bis_no_verificable" && (
  <div className="ml-9 flex items-start gap-1.5">
    <Database className="size-3 shrink-0 mt-0.5 text-muted-foreground" />
    <p className="text-xs text-muted-foreground">
      Verificado contra datos SAT importados en este sistema
    </p>
  </div>
)}
```

Import `Database` from `lucide-react`.

- [ ] **Step 2: Update callers in report page**

In `frontend/app/expedientes/[id]/reporte/page.tsx`, find where `ActionCard` is rendered and add `expedienteId={id}`:
```tsx
<ActionCard
  key={i}
  accion={accion}
  relatedFactor={...}
  index={i}
  expedienteId={id}
/>
```

- [ ] **Step 3: TypeScript + build**

```bash
cd frontend && pnpm exec tsc --noEmit && pnpm build 2>&1 | tail -20
```
Expected: no errors

- [ ] **Step 4: Commit**

```bash
cd frontend
rtk git add components/ActionCard.tsx app/expedientes/[id]/reporte/page.tsx
rtk git commit -m "feat: ActionCard uses contextual nav links — removes blocked SAT external links"
```

---

### Task 17: Dashboard — demo seed button

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `api.seedDemo()` from Task 9
- Produces: "Cargar datos de demo" button in empty state and in header; calls seedDemo + mutates expedientes list

- [ ] **Step 1: Add seed button to dashboard**

In `frontend/app/page.tsx`, add state and handler:
```typescript
const [seeding, setSeeding] = useState(false);
const { mutate } = useExpedientes(); // already exists

async function handleSeedDemo() {
  setSeeding(true);
  try {
    await api.seedDemo();
    toast.success("3 expedientes demo cargados y evaluados");
    await mutate();
  } catch {
    toast.error("Error al cargar datos de demo");
  } finally {
    setSeeding(false);
  }
}
```

In the empty state (when `expedientes.length === 0`), add prominently:
```tsx
<div className="text-center py-12 space-y-4">
  <p className="text-muted-foreground">No hay expedientes. Comenzá cargando los datos de demo.</p>
  <Button onClick={handleSeedDemo} disabled={seeding} className="bg-primary text-primary-foreground">
    {seeding ? "Cargando…" : "Cargar datos de demo"}
  </Button>
</div>
```

In the header (always visible), add a secondary button:
```tsx
<Button
  variant="outline"
  size="sm"
  onClick={handleSeedDemo}
  disabled={seeding}
  title="Recarga los 3 expedientes demo (limpia los anteriores)"
>
  {seeding ? "…" : "Demo"}
</Button>
```

- [ ] **Step 2: TypeScript + final build check**

```bash
cd frontend && pnpm exec tsc --noEmit && pnpm build 2>&1 | tail -30
```
Expected: BUILD SUCCESSFUL, no TS errors

- [ ] **Step 3: Commit**

```bash
cd frontend
rtk git add app/page.tsx
rtk git commit -m "feat: dashboard demo seed button — loads 3 expedientes with evaluations in one click"
```

---

## E2E VERIFICATION (After backend + frontend tasks complete)

- [ ] Run full backend test suite: `cd backend && uv run pytest src/tests/ -v`
  Expected: all green, 100+ tests passing

- [ ] Verify demo data flow manually (or via seed script):
  - Scenario 1 (EKU9003173C9): decision=`safe`, score < 30
  - Scenario 2 (COX010101AB1): decision=`review_required`, score 30–69 (razón social discrepancy fires)
  - Scenario 3 (AAA120730823): decision=`review_required` or `high_risk` (manifestacion_incompleta + check SAT data)

- [ ] Deploy backend to Vercel: `vercel --prod` from `backend/`

- [ ] Deploy frontend to Vercel: `vercel --prod` from `frontend/`

- [ ] Smoke test deployed app:
  - Click "Cargar datos de demo" → 3 expedientes appear
  - Open Scenario 2 → score shows "X pts de riesgo" (no "/ 100")
  - Upload `rfc.pdf` from demo_pdfs → no CORS error, goes to revisar
  - Delete a document → list updates without page refresh
  - Edit expediente RFC → saves, header updates without refresh

---

## Self-Review

**Spec coverage:**
- ✅ Bug 1 (rfc SCHEMA_REGISTRY + CORS) → Task 1
- ✅ Bug 2 (fecha_emision level) → Task 2
- ✅ Bug 3 (score display) → Task 11
- ✅ Bug 4 (discrepancias no tests) → Task 3
- ✅ Bug 5 (extract uses local path) → Task 5
- ✅ Bug 6 (SAT links blocked) → Task 16
- ✅ Bug 7 (real-time missing) → Tasks 10, 13, 14
- ✅ Gap 1 (delete + re-upload) → Task 6 (backend), Task 13 (frontend)
- ✅ Gap 2 (inline edit) → Task 13
- ✅ Gap 3 (evidence rendering) → Task 15
- ✅ Gap 4 (action nav links) → Task 16
- ✅ Gap 5 (demo seed button) → Tasks 7+9+17
- ✅ Demo PDFs (rfc.pdf) → Task 8
- ✅ Option B (extraction fail → revisar redirect) → Tasks 4+12

**Placeholder scan:** Zero TBDs, TODOs, or "similar to above" — all steps have exact code.

**Type consistency:**
- `UploadDocumentoResult.needs_review: boolean` defined in Task 9, consumed in Task 12 ✓
- `useExpediente`, `useDocumentos`, `useLatestEvaluation` defined in Task 10/14, consumed in Tasks 13/14 ✓
- `ActionCard.expedienteId: string` defined in Task 16, callers updated in same task ✓
- `api.deleteDocumento`, `api.seedDemo` defined in Task 9, consumed in Tasks 13/17 ✓
