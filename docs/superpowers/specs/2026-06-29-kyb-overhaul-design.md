# KYB Platform Overhaul — Design Spec
**Date:** 2026-06-29  
**Scope:** Backend reliability, demo flow, real-time UI, enriched report, TDD  
**Deadline constraint:** Prueba técnica Camtom — already submitted branch; this is the final polish pass.

---

## 1. Problem Summary

The platform is functionally complete but has 7 confirmed bugs and 5 UX gaps that make it fall short of "excellent technical assessment" quality. This spec addresses all of them in a single sprint.

---

## 2. Confirmed Bugs

### Bug 1 — `rfc` not in SCHEMA_REGISTRY (CORS on upload)
- **File:** `backend/src/infrastructure/ai/schemas.py:49`
- **Root cause:** `"rfc"` is listed in `DOCUMENTOS_ESPERADOS` (the set the scoring engine checks) but missing from `SCHEMA_REGISTRY`. When the user uploads `rfc.pdf`, the endpoint raises `HTTPException(422)`. In the Vercel serverless runtime, multipart form parse + HTTPException sometimes produces a response without the CORS `Access-Control-Allow-Origin` header, causing a browser-side CORS block.
- **Fix:** Add `RfcFields(BaseModel)` with fields `rfc`, `razon_social`, `domicilio_fiscal` (all `str | None = None`) and register it as `"rfc": RfcFields` in `SCHEMA_REGISTRY`.

### Bug 2 — `fecha_emision` reads wrong dict level (silent, never fires)
- **File:** `backend/src/domain/scoring/factors.py:61–67`
- **Root cause:** `doc.get("fecha_emision")` reads a column that doesn't exist at the row level. The value is stored as `doc["fields"]["fecha_emision"]` (a string, ISO 8601). Both `doc_expired` and `csf_stale` factors NEVER trigger.
- **Fix:**
  ```python
  fecha_str = (doc.get("fields") or {}).get("fecha_emision")
  if fecha_str:
      from datetime import date as date_type
      fecha = date_type.fromisoformat(fecha_str)
      # then do arithmetic with fecha
  ```

### Bug 3 — Score display "/ 100" when raw sum can exceed 100
- **File:** `frontend/components/ScoreGauge.tsx:20`, `backend/src/domain/scoring/engine.py:15`
- **Root cause:** `score_total` is the raw additive sum — 8 missing docs × 15 pts = 120. The gauge clamps the bar but still displays "120 / 100" which confuses non-technical users. The thresholds (30/70) are CORRECT and must not change.
- **Fix (frontend):** Change label to "X pts de riesgo" without the "/ 100" cap. Add a static legend below: "< 30 aprobado · 30–69 revisión · 70+ bloqueado". In `DecisionContext` explanation, replace "Scores por debajo de 30 son aprobados" with a per-band sentence that mentions score without implying a 100-point ceiling.

### Bug 4 — `factores_discrepancias` has zero test coverage
- **File:** `backend/src/domain/scoring/factors.py:29–41`
- **Root cause:** Codegraph flagged `⚠️ no covering tests found`. Highest-weight single factor (50 pts for `disc_rfc`) is untested.
- **Fix:** Add `test_scoring_factors_discrepancias.py` covering all 5 branches: each flag individually + combined + all-clean case.

### Bug 5 — `extract_documento` route reads storage_path as local file path
- **File:** `backend/src/api/routers/documentos.py:58`
- **Root cause:** `extraer_texto(doc["storage_path"])` calls `PdfReader(pdf_path)` where `pdf_path` is a Supabase Storage key like `expediente_id/doc_type.pdf`, not a local filesystem path. On Vercel this always fails with FileNotFoundError, silently returning a 500.
- **Fix:** Download bytes from Supabase Storage first, then call `extraer_texto_de_bytes(content)`.

### Bug 6 — SAT external links blocked
- **File:** `frontend/components/ActionCard.tsx:37,49,59,71,148`
- **Root cause:** `verifyUrl` fields link to `sat.gob.mx` pages that Vercel's CDN and many browsers can't reach (government CORS restrictions, geographic firewall). Users see dead links.
- **Fix:** Replace external `verifyUrl`/`verifyLabel` with an internal note: show the SAT import date from `sat_import_runs` (already stored in DB) and a message "Verificado contra datos SAT importados el [fecha]". Remove the `<a>` external link. Keep legal ref text intact.

### Bug 7 — Real-time updates missing on detail and report pages
- **File:** `frontend/app/expedientes/[id]/page.tsx`, `frontend/app/expedientes/[id]/reporte/page.tsx`
- **Root cause:** Only the dashboard (`/`) uses SWR. Detail and report pages use `router.refresh()` (Next.js server cache) which causes a full round-trip + visible flash, and doesn't update other open tabs.
- **Fix:** Convert both pages to SWR client components with the same `useExpedientes` pattern. After each mutation (upload, delete, evaluate), call `mutate()` instead of `router.refresh()`.

---

## 3. UX Gaps

### Gap 1 — No delete + re-upload flow for documents
Non-technical users upload a wrong PDF and have no recourse. Need: delete button on each document card (with confirmation dialog), which removes the DB record and Storage object, then re-opens the uploader for that slot.

### Gap 2 — No inline edit for expediente metadata
To fix a RFC typo the user must navigate away. Need: pencil icon on the expediente header that opens a dialog with all 4 editable fields (razón social, RFC, domicilio, representante). Uses existing `PATCH /expedientes/{id}` endpoint.

### Gap 3 — KYB report factors don't show actual evidence data
`FactorDetailCard` shows the factor label and legal ref but not the WHY. The backend's `evidence` dict contains the exact data point (e.g., `{"doc_type": "comprobante_domicilio"}`, `{"documento_id": "uuid"}`, `{"manual_review_required": true}`). Render that data in plain language.

### Gap 4 — Report actions don't link back to the corrective page
Each `ActionCard` describes what to do but provides no navigation. "Cargar documento faltante" should link to the expediente detail page filtered to that doc type slot. "Revisar campos" should deep-link to `/expedientes/{id}/revisar?documento_id={id}`.

### Gap 5 — No demo data loader in the UI
`seed_demo_data.py` correctly populates the DB bypassing AI extraction, but users have to run it from CLI. Need a `POST /demo/seed` endpoint and a "Cargar datos de demo" button on the empty state of the dashboard.

---

## 4. Architecture Decisions

### 4.1 RfcFields schema
```python
class RfcFields(BaseModel):
    rfc: str | None = None
    razon_social: str | None = None
    domicilio_fiscal: str | None = None
```
The physical RFC document (Cédula de Identificación Fiscal) always shows these 3 fields. Adding them to the schema means Groq will extract them, the `revisar` page will show them for human review, and reconciliation can compare RFC across all docs.

### 4.2 Upload extraction failure → option B
When `extraer_campos()` fails (exception, empty result, or the doc has no text): save the document with `extraction_status: "pending"`, return HTTP 200 with `{"documento_id": "...", "extraction_status": "pending", "needs_review": true}`. The frontend `DocumentUploader` detects `needs_review: true` and redirects to `/expedientes/{id}/revisar?documento_id={doc_id}` with a banner "La IA no pudo extraer los campos — completá los datos manualmente."

### 4.3 SWR strategy for detail/report pages
Both pages become `"use client"` with `useSWR` hooks:
- `/expedientes/{id}` → `useExpediente(id)`
- `/documentos?expediente_id={id}` → `useDocumentos(id)`
- `/expedientes/{id}/evaluations/latest` → `useLatestEvaluation(id)`

After each write operation, call `mutate()` on the relevant key. No `router.refresh()` except for navigation-triggered refreshes.

### 4.4 Demo seed endpoint
`POST /demo/seed` runs the same logic as `seed_demo_data.py:seed()` inline (no subprocess). Returns `{expediente_ids: [...], message: "3 expedientes seeded"}`. No auth required — this is a prueba técnica demo, not a production system. The endpoint also cleans previous demo data before re-seeding (idempotent). The "Cargar datos de demo" button lives in the dashboard empty state (shown when `expedientes.length === 0`) and also as a secondary button when the list has items (to allow reset).

### 4.5 SAT date instead of external links
Each `ActionCard` that currently has a `verifyUrl` will instead show: "Fuente: datos SAT importados el [fecha del import más reciente]". This data is already available via `GET /admin/sat-import-runs`. The frontend fetches it once on the report page and passes it down.

---

## 5. Data Flow Changes

### upload_documento (revised)
```
POST /documentos/upload
  → validate expediente_id (UUID) 
  → validate doc_type in SCHEMA_REGISTRY  ← now includes "rfc"
  → check duplicate
  → upload bytes to Supabase Storage
  → extraer_texto_de_bytes(content)
  → try: extraer_campos(...)
    success → extraction_status: "extracted"
    fail/empty → extraction_status: "pending", needs_review: True
  → insert documentos row
  → return {documento_id, extraction_status, needs_review}
```

### factores_completitud (revised fecha_emision reads)
```python
fields = doc.get("fields") or {}
fecha_str = fields.get("fecha_emision")
fecha = date.fromisoformat(fecha_str) if fecha_str else None
if doc["doc_type"] == "comprobante_domicilio" and fecha:
    if (hoy - fecha).days > VIGENCIA_DIAS["comprobante_domicilio"]:
        # fire doc_expired
if doc["doc_type"] == "csf" and fecha:
    if (fecha.year, fecha.month) != (hoy.year, hoy.month):
        # fire csf_stale
```

---

## 6. Test Coverage Requirements

Every new/fixed code path must have a corresponding test. Minimum additions:

| Module | Tests to add |
|---|---|
| `test_scoring_factors_discrepancias.py` | 5 branches: each flag + combined + clean |
| `test_scoring_factors_completitud.py` | Add: doc_expired fires, csf_stale fires, rfc doc has RfcFields schema, `fecha_emision` from fields not top-level |
| `test_upload_endpoint.py` | Add: rfc doc_type succeeds, Groq fail → 200 + pending status, storage fail → 500 with CORS header present |
| `test_rfc_schema.py` | RfcFields in SCHEMA_REGISTRY, extraction of rfc text |
| `test_demo_seed.py` | Seed creates 3 expedientes, evaluations match expected decisions |

---

## 7. Demo PDF Regeneration

The 24 demo PDFs need richer content so Groq can extract fields correctly. For `rfc.pdf` specifically, add the 3 fields now in `RfcFields`:

```
CÉDULA DE IDENTIFICACIÓN FISCAL
RFC: EKU9003173C9
Razón Social: Escuela Kemper Urgate SA de CV
Domicilio Fiscal: Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700
```

All other PDFs already extract correctly (confirmed by user). Keep them as-is.

---

## 8. Non-goals (YAGNI)

- Autenticación / login — explicitly out of scope
- Admin page rework — already removed from nav
- Export PDF report — not requested
- Pagination of expedientes list — <20 items in demo

---

## 9. Implementation Order (dependency-safe)

1. Backend: `RfcFields` in SCHEMA_REGISTRY + TDD
2. Backend: `fecha_emision` fix in `factores_completitud` + TDD
3. Backend: `upload_documento` extraction fail → option B response + TDD
4. Backend: `extract_documento` fix (use Storage bytes, not local path) + TDD
5. Backend: `POST /demo/seed` endpoint + TDD
6. Backend: TDD for `factores_discrepancias` (existing code, new tests)
7. Frontend: SWR on expediente detail and report pages
8. Frontend: Document delete + re-upload flow
9. Frontend: Expediente inline edit dialog
10. Frontend: `DocumentUploader` option B (needs_review redirect)
11. Frontend: `FactorDetailCard` evidence rendering
12. Frontend: `ActionCard` — remove broken SAT links, add contextual nav links
13. Frontend: `ScoreGauge` label fix (remove "/ 100")
14. Frontend: Demo seed button on empty state
15. Demo: Regenerate `rfc.pdf` for all 3 scenarios with correct content
16. E2E: Run `seed_demo_data.py` against staging, verify 3 scenarios score correctly
