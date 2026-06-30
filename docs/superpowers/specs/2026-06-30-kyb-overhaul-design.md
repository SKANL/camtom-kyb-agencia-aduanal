# KYB Platform — Full Overhaul Design Spec
**Date:** 2026-06-30  
**Status:** Approved by user  
**Scope:** 6 critical bugs → demo correctness; AI multi-model; enhanced report; UI/UX (real-time, responsive, no raw JSON); CRUD; DB cleanup; demo PDF regeneration.

---

## 1. Context

The platform was delivered yesterday with a previous bug-fix pass (PR #17, commits up to `1034ac3`).
Six NEW critical bugs were identified in this session via CodeGraph + codebase deep-read.
All scenarios are broken: scenario 1 can never be `safe`, scenario 2 can land as `high_risk` instead of `review_required`.

---

## 2. Critical Bugs (root-caused)

### Bug A — `rfc` doc type absent from ALL frontend lists
- **Where:** `frontend/components/SmartDropZone.tsx:10` (`DOC_TYPE_OPTIONS`) and `frontend/app/expedientes/[id]/page.tsx:26` (`DOC_TYPE_LABELS`)
- **Root cause:** `rfc` is in the backend's `SCHEMA_REGISTRY` (8 types) and `DOCUMENTOS_ESPERADOS` (8 types), but both frontend maps only have 7 entries. The drop-zone can't classify or display `rfc.pdf`. Progress bar shows 7/7 instead of 8/8.
- **Fix:** Add `{ value: "rfc", label: "Cédula de Identificación Fiscal" }` to `DOC_TYPE_OPTIONS`, add `rfc: "Cédula de Identificación Fiscal"` to `DOC_TYPE_LABELS`.

### Bug B — Socios check reads empty DB table (scenario 1 can never be safe)
- **Where:** `backend/src/services/evaluation_service.py:13` and `backend/src/domain/scoring/factors.py:82`
- **Root cause:** `factores_completitud(documentos, socios, hoy)` receives `socios` from `supabase.table("socios")` which is NEVER populated by the document review flow. The extracted `fields.socios` (from ActaConstitutivaFields) is stored in `documentos.fields` but never synced to the `socios` table. Result: `socios_incompletos` (+20 pts) always fires for any expediente with an acta constitutiva. Scenario 1 starts at +20 pts before AI even touches it.
- **Fix:** In `evaluation_service.py`, extract socios from the acta document's `fields.socios` instead of querying the `socios` table. Pass the extracted list to `factores_completitud`. No DB schema changes needed.

### Bug C — `manifestacion_protesta` boolean extraction unreliable
- **Where:** `backend/src/infrastructure/ai/schemas.py:39`, `backend/src/infrastructure/ai/extract.py:5`
- **Root cause:** `ManifestacionProtestaFields.declara_no_69b_49bis: bool = False`. The extraction prompt is generic ("extrae solo lo que aparece literalmente") with no guidance on how to interpret legal clauses as a boolean. If Groq is uncertain, it returns `False` → `manifestacion_incompleta` (+20 pts) fires on scenario 1. Additionally, `False` as default means "absent" is indistinguishable from "declared negative".
- **Fix (two parts):**
  1. Make field `bool | None = None`. In `factores_completitud`, only add `manifestacion_incompleta` when `declara_no_69b_49bis is False` (explicit negative), not when `None` (absent/uncertain).
  2. Add doc-type-specific hints to the extraction prompt for `manifestacion_protesta`: explain that the field is `True` when the text contains clauses stating the declarant is NOT in Art. 69-B / 49 Bis CFF lists.

### Bug D — Flash "Expediente no encontrado" during initial load
- **Where:** `frontend/app/expedientes/[id]/page.tsx:113`, `frontend/app/expedientes/[id]/reporte/page.tsx` (same pattern)
- **Root cause:** `useExpediente` SWR hook returns `expediente: undefined` during initial fetch. The component checks `if (!expediente)` and renders the 404 UI. SWR's `isLoading` is not checked.
- **Fix:** Differentiate `isLoading` (show skeleton) from `!expediente && !isLoading` (show 404). Apply same pattern to reporte page.

### Bug E — "Next doc" button navigates to non-reviewable docs
- **Where:** `frontend/app/expedientes/[id]/revisar/page.tsx:259`
- **Root cause:** `remainingDocs` filter includes `extraction_status === "not_applicable"` (manual-entry docs). Navigating to a `not_applicable` doc shows "Sin campos para revisar" — a dead end. Also, after saving a document, the `listDocumentos` call may return stale data if the SWR cache is not invalidated.
- **Fix:** Change filter to `extraction_status === "extracted"` only. After confirmar(), call `mutate` on the documentos SWR key to force refresh before computing remainingDocs.

### Bug F — All AI tasks use same model (no specialization)
- **Where:** `backend/src/infrastructure/ai/groq_client.py:5`, `backend/src/infrastructure/ai/classify.py`, `backend/src/infrastructure/ai/similarity.py`
- **Root cause:** Single `MODEL_EXTRACCION = "llama-3.3-70b-versatile"` used everywhere. Classification is a simple multi-class task that doesn't need 70B parameters. Semantic similarity needs strong reasoning.
- **Fix:** Create `get_groq_model_for(task: str) -> ChatGroq` with task-specific model selection:
  - `"classification"` → `"llama-3.1-8b-instant"` (fast, cheap, 8k context)
  - `"extraction"` → `"llama-3.3-70b-versatile"` (keep — accuracy matters)
  - `"similarity"` → `"qwen/qwen3-32b"` (strong semantic reasoning)
  - `"guard"` → `"meta-llama/llama-prompt-guard-2-22m"` (lightweight, prompt injection detection)

---

## 3. AI Multi-model Architecture

```
classify.py  ──► llama-3.1-8b-instant     (classification: fast + cheap)
extract.py   ──► llama-3.3-70b-versatile  (extraction: accuracy first)
similarity.py ──► qwen/qwen3-32b          (reasoning: entity comparison)
```

No change to harness caching logic — the cache key includes the model name implicitly through the content hash. Models are environment-configurable (env vars override defaults).

---

## 4. Enhanced KYB Report

### 4A. Factor cards show WHAT was compared
- `disc_*` factors: include `compared_values: { a: str, b: str }` in the `evidence` dict (set by reconciliation service). Frontend `FactorDetailCard` renders these as "El expediente dice X — el documento dice Y".
- `doc_expired` / `csf_stale`: evidence already includes `dias_antiguedad` and `fecha_csf`. Render these prominently.

### 4B. Decision narrative ("¿Por qué esta decisión?")
A new `DecisionContext` component (already exists) that explains:
- The 2–3 highest-weight factors by name
- The regulatory basis (Regla 1.4.14 RGCE 2026, specific CFF articles)
- What would change the outcome (e.g., "resolve disc_rfc and the score drops to 25 → aprobado")

### 4C. Suggested actions with verifiable citations
`FACTOR_ACTIONS` already has detailed steps. Add:
- `legal_article`: short quote from the actual article (e.g., CFF Art. 69-B first paragraph)
- `responsible`: who takes the action (`"cliente"` / `"agente"` / `"SAT"`)
- `time_estimate`: typical turnaround

### 4D. Inter-page action links
- `disc_*` factors → link directly to `revisar?documento_id=<id>` of the conflicting doc
- `doc_missing` → link to expediente with the missing doc type pre-highlighted
- `csf_stale`, `doc_expired` → link to expediente with the specific doc card

---

## 5. UI/UX Improvements

### 5A. Real-time updates (SWR revalidation)
- `SmartDropZone`: replace `router.refresh()` with `mutateDocumentos()` after upload
- `EvaluateButton`: already uses `mutate()` — verify it invalidates `use-expediente` key too
- `revisar/page.tsx`: after `confirmar()`, call `mutateDocumentos()` instead of relying on re-fetch

### 5B. Responsive design
- `ExpedienteDetailPage`: documents grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- `RevisarPage`: stack left/right columns vertically on mobile (`lg:grid-cols-2`, col-1 first)
- `ReportePage`: factor cards are already single-column — verify ActionCard wraps correctly
- Dashboard: ExpedientesList table → card layout on small screens
- StepperHeader: collapse step labels on mobile

### 5C. No raw JSON anywhere
- `socios` display in revisar/page.tsx `FieldDisplay`: render as a structured list (name, RFC, %)
- `evidence` display: `EvidenceDisplay` already handles most cases — add `compared_values` rendering

### 5D. CRUD completeness
- **Create expediente**: already works (modal in dashboard)
- **Edit expediente**: already works (inline edit in detail page)
- **Delete expediente**: already works (ExpedienteActions)
- **Delete documento**: already works (button in detail page)
- **ADD MISSING**: replace document (delete + re-upload flow) — currently the user must delete then re-upload separately. Add a "Reemplazar" button on each doc card.

### 5E. Loading skeleton for detail/report pages
Replace "Expediente no encontrado" flash with proper skeleton cards during SWR initial load.

---

## 6. Demo Data & Database Cleanup

### 6A. Wipe DB expedientes
Use Supabase to DELETE all rows from `expedientes` (cascades to `documentos`, `evaluations`, `consultas_sat`, `audit_log` via FK).

### 6B. Verify SAT data
Check backend/data/sat CSVs:
- `EKU9003173C9` → NOT in any SAT list (clean scenario)
- `COX010101AB1` → NOT in any SAT list (discrepancy scenario — risk comes from docs, not SAT)
- `AAA120730823` → IN `art69b_definitivos` (high risk via critical block)

### 6C. Regenerate demo PDFs
After fixing bugs A, B, C, regenerate and verify expected scores:
- Scenario 1 (`EKU9003173C9`): expected 0 pts → `safe`
- Scenario 2 (`COX010101AB1`): expected ≤69 pts → `review_required` (disc_razon_social 30 + disc_representante 25 = 55)
- Scenario 3 (`AAA120730823`): expected `high_risk` via `sat_69b_definitivo` critical block

---

## 7. TDD Requirements

All backend changes require tests BEFORE implementation:
- `test_scoring_factors_completitud.py`: add test for socios-from-doc-fields path
- `test_scoring_factors_completitud.py`: add test for manifestacion with `None` → no penalty
- `test_scoring_factors_completitud.py`: add test for manifestacion with `False` → +20 pts
- `test_ai_schemas.py`: add test for ManifestacionProtestaFields with `None` default
- `test_evaluation_service.py`: end-to-end scenario 1 (safe), scenario 2 (review_required), scenario 3 (high_risk)
- `test_reconciliation_service.py`: verify compared_values appear in reconciliation result

---

## 8. Out of Scope

- Admin backend routes (`/admin/sat-import-runs`, `/admin/ingest/{list_type}`) — keep as-is, they're useful for SAT data management even if not exposed in the frontend
- `socios` DB table — leave it in the schema but stop reading from it for the scoring check
- Authentication — explicitly out of scope per original brief

---

## 9A. Additional Bugs Found (2026-06-30 second pass)

These are NEW bugs not in the original 6, found by deep codebase exploration:

### Bug G — `doc_data_incomplete` fires for optional null fields
- **Where:** `backend/src/domain/scoring/factors.py:59`
- **Root cause:** `any(v in (None, "") for v in fields.values())` checks ALL fields, including optional ones like `regimen_fiscal` (CSF), `alcance` (poder_notarial), `fecha_vencimiento` (ID). A clean scenario 1 with proper human review still accumulates 15 pts × N docs with optional null fields.
- **Fix:** Define `REQUIRED_FIELDS: dict[str, set[str]]` per doc type. Only check required fields.

### Bug H — No DOC_TYPE_HINT for `acta_constitutiva` socios
- **Where:** `backend/src/infrastructure/ai/extract.py:13` (`DOC_TYPE_HINTS`)
- **Root cause:** There's no per-doc-type hint for acta. The AI doesn't know how to map `"Juan Pérez García (60%)"` to `{nombre, rfc, porcentaje}`. The AI may return `socios: []` or partially structured data.
- **Fix:** Add `"acta_constitutiva"` hint explaining the socios structure with examples.

### Bug I — Demo PDF socios have no RFC numbers
- **Where:** `backend/scripts/generate_demo_pdfs.py:279-280`
- **Root cause:** Socios are listed as `"Juan Pérez García (60%)"` without RFC. Even with a perfect extraction hint, the AI cannot extract a field that isn't there. The `socios_incompletos` factor checks `if acta and not socios` — but the SociosEditor requires RFC to be useful.
- **Fix:** Add RFC numbers to socios in all 3 escenario acta PDFs.

### Bug J — `art_49bis_no_verificable` (0 pts) shown in factor list
- **Where:** `backend/src/domain/scoring/factors.py:26`, frontend report page
- **Root cause:** This informational factor always appears in the scored factors list, displayed alongside real risk factors. Non-technical users don't understand why a "factor" has 0 pts and what "no verificable" means.
- **Fix:** In `evaluar_expediente`, separate factors with 0 pts and `evidence.manual_review_required` into a `factores_informativos` list. Frontend shows them as a distinct "Notas" section.

### Bug K — SWR invalidation gaps in upload + review flows
- **Where:** `frontend/components/SmartDropZone.tsx`, `frontend/app/expedientes/[id]/revisar/page.tsx`
- **Root cause:** After upload or review confirmation, the document list doesn't refresh in the parent page (expediente detail). The user sees stale document states (pending/extracted) until browser refresh.
- **Fix:** Add `mutate("documentos-${expedienteId}")` after upload and after review confirmation.

### Bug L — Expediente detail page uses server-side fetch, not SWR
- **Where:** `frontend/app/expedientes/[id]/page.tsx`
- **Root cause:** The page fetches expediente and documentos server-side. After evaluate, the score in the expediente card doesn't update without full page refresh. `useExpediente` hook exists but isn't used on the detail page.
- **Fix:** Migrate detail page fetch to `useExpediente` + `useDocumentos` SWR hooks.

---

## 9. Implementation Order

Dependencies:
```
Bug B (socios) ──┐
Bug C (manifest) ─┼──► Demo PDFs verified ──► DB cleanup + re-test
Bug A (rfc UI) ──┘

Bug D (flash) ──┐
Bug E (next-doc) ──┘──► UX improvements

Bug F (AI models) → independent, no dependencies

Enhanced report → depends on Bug B (socios) fix being in place
Responsive design → independent
```

Parallel execution plan:
- **Parallel A**: Backend bugs (B, C, F) + TDD
- **Parallel B**: Frontend bugs (A, D, E) + responsive + real-time
- **After A completes**: Demo PDF verification + DB cleanup
- **After A + B complete**: Enhanced report (needs correct data) + integration test
