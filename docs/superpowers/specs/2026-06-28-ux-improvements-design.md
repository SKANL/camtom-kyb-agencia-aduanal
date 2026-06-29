# UX/UI Overhaul — KYB Platform Design Spec

**Date:** 2026-06-28  
**Branch:** feat/ux-improvements  
**Author:** Gaspar (Camtom technical test)

---

## Problem

The current frontend is functionally complete but has three critical UX gaps:

1. **Broken flow**: After creating an expediente, the user is redirected to `/reporte` before uploading any documents. There is nothing to report yet.
2. **Friction on document upload**: 7 separate file inputs (one per doc type) require the user to know in advance which PDF maps to which document type. No drag & drop, no multi-file upload.
3. **Superficial risk report**: `factores_score` only exposes `code → number`. The backend `Factor` dataclass already has `detail`, `is_critical_block`, and `evidence` — none of it is returned by the API or shown in the UI. The report has no legal citations, no "why this matters", nothing an auditor can rely on.

---

## Goals

- Make the platform look and feel like a professional KYB product, not a weekend project
- Reduce upload friction to zero: drop any files, in any order, from any folder
- Surface the legal and evidential basis of every risk decision
- Complete the linear KYB workflow with no dead ends or missing transitions

---

## User Flow (4 Steps)

```
[1] Datos empresa  →  [2] Cargar docs  →  [3] Pipeline  →  [4] Reporte
/expedientes/nuevo    /expedientes/[id]    (inline)         /expedientes/[id]/reporte
```

A persistent stepper component shows the current step in all four pages.

---

## Section 1 — Step 1: Datos de Empresa (`/expedientes/nuevo`)

**Changes from current:**
- Add stepper header (Step 1 of 4)
- Add inline RFC format validation (12/13 chars, regex pattern) with real-time feedback
- On success, redirect to `/expedientes/{id}` (not `/reporte` — this is the main bug fix)
- Better empty state labels with examples (e.g., RFC: `EKU9003173C9`)

---

## Section 2 — Step 2: Smart Document Upload (`/expedientes/[id]`)

### New backend endpoint: `POST /documentos/classify`

```
Request:  multipart/form-data { file: PDF }
Response: { doc_type: string, confidence: "high" | "low", suggested_label: string }
```

Uses Groq (same infrastructure as extraction) with a classification prompt:
> "Read the following document text and return the document type. Options: csf, acta_constitutiva, comprobante_domicilio, identificacion_rep_legal, poder_notarial, encargo_conferido, manifestacion_protesta. Return JSON: {doc_type, confidence}"

### Frontend — Drop Zone Component (`SmartDropZone`)

- Full-width drop zone (dashed border, icon, label "Arrastrá tus PDFs aquí")
- Accepts `multiple`, `webkitdirectory` for folder drops
- On drop: each file is immediately sent to `/documentos/classify` in parallel
- Shows classification result per file:
  - `✓ acta_constitutiva.pdf → Acta Constitutiva` (high confidence)
  - `⚠ documento_123.pdf → Sin clasificar` (low confidence — shows select dropdown)
- "Procesar todos" button: disabled until all files have a doc_type assigned
- On process: uploads and extracts all files in parallel, shows per-file progress

### Existing doc-type cards (kept but simplified)
- Cards still show upload status and "Revisar →" link
- If a doc_type already has a document (uploaded or reviewed), the card is locked
- The SmartDropZone replaces individual uploaders as the primary interaction

---

## Section 3 — Step 3: Pipeline Visual (inline in Step 2)

Per-file progress row:
```
acta_constitutiva.pdf  [Subiendo ████░░░░] → [Extrayendo] → [Clasificando IA] → ✓ Listo
```

When all files are done: CTA banner → "Revisar campos extraídos" or "Ver reporte KYB"

---

## Section 4 — Step 4: Enhanced Report (`/expedientes/[id]/reporte`)

### Backend API change: `/expedientes/{id}/evaluations/latest`

Add `factores_detail` array to response:

```json
{
  "decision": "review_required",
  "score_total": 75,
  "factores_score": { "disc_domicilio": 20 },
  "factores_detail": [
    {
      "factor_code": "disc_domicilio",
      "points": 20,
      "is_critical_block": false,
      "detail": "El domicilio no coincide de forma material entre los documentos.",
      "evidence": null,
      "legal_ref": "Regla 1.4.14 RGCE 2026 — requisito de coincidencia de domicilio fiscal entre documentos del expediente",
      "category": "discrepancia"
    }
  ],
  "acciones_sugeridas": [...]
}
```

### Legal references map (static, added to backend)

Each `factor_code` maps to a `legal_ref` string:

| factor_code | legal_ref |
|---|---|
| sat_69b_definitivo | Art. 69-B CFF — Listado definitivo EFOS (empresas que facturan operaciones simuladas) |
| sat_69b_presunto | Art. 69-B CFF — Listado presunto EFOS, pendiente de resolución SAT |
| sat_69b_bis | Art. 69-B Bis CFF — Transmisión indebida de pérdidas fiscales |
| sat_69_incumplido | Art. 69 CFF — Contribuyente incumplido con obligaciones fiscales |
| disc_razon_social | Regla 1.4.14 RGCE 2026 — La razón social debe coincidir en todos los documentos del expediente |
| disc_rfc | Regla 1.4.14 RGCE 2026 — El RFC es el identificador fiscal vinculante |
| disc_domicilio | Regla 1.4.14 RGCE 2026 — Domicilio fiscal verificable y consistente |
| disc_representante | Regla 1.4.14 RGCE 2026 — Identidad del representante legal verificable |
| doc_expired | Regla 1.4.14 RGCE 2026 — Comprobante de domicilio con vigencia máxima de 90 días |
| csf_stale | SAT — La CSF debe corresponder al mes calendario vigente |
| doc_missing | Regla 1.4.14 RGCE 2026 — Documentación completa requerida para operar en comercio exterior |
| manifestacion_incompleta | Regla 1.4.14 RGCE 2026 — Manifestación bajo protesta debe incluir renuncia explícita a los Art. 69-B y 49 Bis CFF |

### Frontend — Enhanced FactorRow Component

Each factor shows:
- Factor code → human-readable label
- Points badge (color: red if critical, orange if > 0, green if 0)
- `is_critical_block` → "BLOQUEO CRÍTICO" badge in destructive color
- `detail` text (e.g., "El domicilio no coincide de forma material entre documentos")
- `legal_ref` in small muted text with book icon
- `evidence` JSON if present (e.g., doc_type missing, documento_id)
- Progress bar for relative weight

### Frontend — Enhanced Acciones Sugeridas

Each accion shows:
- Icon (triangle-alert for high, circle-info for medium)
- Action text (existing)
- Legal basis reference tied to the factor_code that triggered it
- Category chip (SAT / Discrepancia / Completitud / Documentos)

### Score Visualization

Replace the large number with:
- Horizontal gauge (0–100) with colored zones: 0-29 green, 30-69 orange, 70+ red
- Current score position marker
- Decision badge prominently placed

---

## Technical Architecture

### New files

**Backend:**
- `backend/src/api/routes/classify.py` — `POST /documentos/classify` endpoint
- `backend/src/domain/scoring/legal_refs.py` — factor_code → legal_ref map

**Frontend:**
- `frontend/components/SmartDropZone.tsx` — multi-file drop zone with classify
- `frontend/components/StepperHeader.tsx` — 4-step progress indicator
- `frontend/components/FactorDetailCard.tsx` — rich factor breakdown card
- `frontend/components/ScoreGauge.tsx` — horizontal score visualization

### Modified files

**Backend:**
- `backend/src/api/routes/expedientes.py` — add `factores_detail` + `legal_ref` to evaluation response
- `backend/src/api/routes/documentos.py` — add `/classify` endpoint

**Frontend:**
- `frontend/app/expedientes/nuevo/page.tsx` — fix redirect + stepper + RFC validation
- `frontend/app/expedientes/[id]/page.tsx` — replace DocumentUploader grid with SmartDropZone
- `frontend/app/expedientes/[id]/reporte/page.tsx` — use FactorDetailCard + ScoreGauge
- `frontend/lib/api-client.ts` — add `classifyDocumento`, update `EvaluationResult` type

---

## Out of scope

- Authentication (explicitly excluded per project brief)
- Batch re-evaluation
- PDF preview in-browser
- Mobile-optimized layout (desktop-first is fine for a KYB ops tool)
