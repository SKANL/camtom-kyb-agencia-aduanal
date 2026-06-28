# KYB Platform — Camtom Technical Challenge

A Know Your Business (KYB) platform for a Mexican customs agency (*agencia aduanal*) that determines whether a *persona moral* is `safe`, `review_required`, or `high_risk` for foreign trade operations under Regla 1.4.14 RGCE 2026.

**Live:**
- Frontend: https://frontend-khaki-eight-25.vercel.app
- Backend API: https://backend-nine-snowy-67.vercel.app

---

## Running locally

### Prerequisites

- Python 3.13 + [`uv`](https://docs.astral.sh/uv/)
- Node.js + [`pnpm`](https://pnpm.io/)
- A Supabase project (cloud — no local Docker stack)
- A Groq API key

### Backend

```bash
# 1. Copy and fill in credentials
cp backend/.env.example backend/.env
# Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GROQ_API_KEY

# 2. Start the API server
cd backend && uv run fastapi dev src/main.py
```

### Frontend

```bash
# 1. Copy and fill in the backend URL
cp frontend/.env.example frontend/.env.local
# Required: NEXT_PUBLIC_API_URL=http://localhost:8000

# 2. Start the dev server
cd frontend && pnpm dev
```

### Tests

```bash
cd backend && uv run pytest src/tests/ -v
```

### Demo data

```bash
# Generate synthetic PDFs (text-selectable, not scanned images)
cd backend && uv run python scripts/generate_demo_pdfs.py

# Seed three test expedientes into the database
cd backend && uv run python scripts/seed_demo.py
```

Three synthetic *expedientes* are seeded:
1. **Clean** — uses SAT's official sandbox RFC `EKU9003173C9`, all documents valid, no list hits.
2. **Mitigable discrepancies** — mismatched *razón social* and address, replicating the brief's sample scenario.
3. **High risk** — RFC present in the Art. 69-B Definitivos list, forces `high_risk` regardless of other factors.

---

## Architecture

```
monorepo/
├── backend/     FastAPI + Python 3.13 (uv)    → Vercel Serverless (Python runtime)
└── frontend/    Next.js 15 App Router + TS     → Vercel Serverless (Node runtime)
```

Each service is deployed as an independent Vercel project. The split is intentional:

- **Separation of concerns** — the UI can be replaced or extended without touching business logic.
- **API-first** — the backend is a standalone REST API consumable by any client (CLI, other systems, future mobile app).
- **Thin frontend** — the Next.js project is purely a presentation layer; it holds no business rules and never touches the database directly.

### Data layer

- **Supabase (cloud-only)** — Postgres for structured data, Storage for PDF blobs. No ORM; the backend uses `supabase-py` with raw SQL for clarity and control. Migrations are versioned in `supabase/migrations/` and applied with `supabase db push`.
- The frontend has zero Supabase access — all reads and writes go through the backend REST API.

### AI layer

- **LangChain + langchain-groq** — Groq hosts Llama inference; LangChain structures the calls.
- The LLM is used for two tasks only: extracting structured fields from PDF text, and semantic reconciliation (comparing form data vs. *Constancia de Situación Fiscal* data).
- **The LLM never decides the final classification.** It returns `similarity` (0–1) and `same_entity` (bool); a deterministic rules engine applies fixed thresholds to produce a score and a verdict.
- Every LLM call passes through `AIHarness` (`infrastructure/ai/harness.py`), which computes a SHA-256 hash of the input and caches the result. Identical input → identical output, always. The model never runs twice on the same content.

---

## Scoring rubric

```
Factor                           Weight   Trigger
─────────────────────────────────────────────────────────────────────────
SAT Art. 69-B Definitivos        +100 pts RFC in EFOS definitive list → CRITICAL BLOCK (forces high_risk)
SAT Art. 69 (embargo/crédito)    +30 pts  RFC in Art. 69 list
Discrepancia razón social        +20 pts  LLM similarity < 0.85 between form name and CSF name
Discrepancia domicilio           +15 pts  LLM similarity < 0.85 between form address and CSF address
Comprobante domicilio vencido    +25 pts  Comprobante fecha_emision > 90 days ago
CSF no vigente                   +30 pts  CSF fecha_emision > 30 days ago
Completitud documental           -10 pts  Per missing required document (up to -50)
─────────────────────────────────────────────────────────────────────────
Decision thresholds:
  safe             → score_total < 30
  review_required  → 30 ≤ score_total < 60
  high_risk        → score_total ≥ 60 OR any CRITICAL BLOCK
─────────────────────────────────────────────────────────────────────────
```

---

## Known limitations

These are conscious design decisions, not omissions.

| Area | Status | Reason |
|---|---|---|
| **Art. 49 Bis** (contrabando técnico) | Not implemented | SAT publishes no public list for this article — documented as a known gap, not fabricated |
| **Art. 69-B Bis** | Schema ready, ETL partial | SAT only exposes this via a dynamic web form with no downloadable XLSX; download step is manual |
| **OCR fallback** | Available (`pdf2image` + `pytesseract`) | Groq's Llama does not accept images — OCR extracts text which then feeds the LLM pipeline; quality depends on scan resolution |
| **VUCEM / Opinión de Cumplimiento** | Out of scope | Would require CIEC credentials and SAT web scraping — not appropriate for a sandboxed demo |
| **Authentication** | None | Conscious decision: no auth = no friction for evaluators |
| **Supabase Storage download** | `extract_documento` reads `storage_path` as a local path | In production, this step must first download the blob from Supabase Storage before processing |

---

## How AI is used — and why the verdict is still deterministic

The platform uses AI for perception (reading documents), not for judgment (deciding outcomes).

**Extraction phase:** Groq Llama receives the raw text of a PDF and returns structured fields (*RFC*, *razón social*, *domicilio*, *fecha_emision*). This replaces brittle regex parsing and handles layout variation across document issuers.

**Reconciliation phase:** Groq Llama compares two strings (e.g., the *razón social* the applicant typed in the form vs. the name on the *Constancia de Situación Fiscal*) and returns a `similarity` score and a `same_entity` boolean.

**Scoring phase (deterministic):** The rules engine receives those metrics and applies hard-coded thresholds. A similarity below 0.85 adds 20 points — the model has no say in what that threshold is or what it implies. A score ≥ 60 is always `high_risk`; there is no "but the AI thinks it's fine" override.

**Harness engineering:** `AIHarness` wraps every LLM call with a SHA-256 content hash. The result is cached so that re-evaluating the same document with the same data produces byte-identical output without hitting the model again. This makes the platform fully auditable: given the same documents, the same RFC, and the same SAT fiscal lists, the decision will always be identical.

---

## Implementation plan

The full architecture decisions, data model, exact scoring rationale, and granular TDD task breakdown are in:

[`docs/superpowers/plans/2026-06-27-kyb-agencia-aduanal.md`](docs/superpowers/plans/2026-06-27-kyb-agencia-aduanal.md)
