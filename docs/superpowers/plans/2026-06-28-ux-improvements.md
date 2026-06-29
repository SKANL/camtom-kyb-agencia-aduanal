# UX/UI Overhaul — KYB Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the KYB frontend with a 4-step wizard flow, intelligent multi-file drag-and-drop upload with AI auto-classification by content, and a rich risk report with legal citations surfaced from the backend's Factor objects.

**Architecture:** Backend gains two changes: (1) `POST /documentos/classify` endpoint (reuses Groq, no DB write, accepts multipart PDF) and (2) evaluation response expanded with full `factores_detail` array + `factores_score` stored in `summary` JSONB. Frontend gains 4 new components (StepperHeader, ScoreGauge, FactorDetailCard, SmartDropZone) and existing pages are refactored into a linear 4-step wizard.

**Tech Stack:** FastAPI + Python 3.13 + pdfplumber + langchain-groq (backend); Next.js 15 App Router + TypeScript + Tailwind + shadcn/ui (frontend); pnpm (frontend), uv run (backend)

## Global Constraints

- Python 3.13 — use `uv run pytest` never `python -m pytest`
- All backend commands: `cd backend && uv run <cmd>`
- All frontend commands: `cd frontend && pnpm <cmd>`
- TDD strict on backend: test → fail → implement → pass → commit
- Frontend: visual verification with `pnpm dev`, no unit test requirement
- UI copy in Spanish, code identifiers in English — match existing convention
- Never hardcode secrets; existing `.env` / `.env.local` already configured

---

## File Map

**New backend files:**
- `backend/src/domain/scoring/legal_refs.py` — static map: factor_code → {ref, category}
- `backend/src/infrastructure/ai/classify.py` — `clasificar_documento(texto: str) -> dict`

**Modified backend files:**
- `backend/src/infrastructure/ai/pdf.py` — add `extraer_texto_de_bytes(content: bytes) -> str`
- `backend/src/services/evaluation_service.py` — save `factores_score` + `factores_detail` in summary; return them
- `backend/src/api/routers/expedientes.py` — fix `get_latest_evaluation` to read factores from summary
- `backend/src/api/routers/documentos.py` — add `POST /documentos/classify` endpoint

**New frontend files:**
- `frontend/components/StepperHeader.tsx` — 4-step progress indicator
- `frontend/components/ScoreGauge.tsx` — horizontal colored gauge (0–100)
- `frontend/components/FactorDetailCard.tsx` — rich factor card with legal ref
- `frontend/components/SmartDropZone.tsx` — multi-file drop zone with AI classify

**Modified frontend files:**
- `frontend/lib/api-client.ts` — add `FactorDetail` type, update `EvaluationResult`, add `classifyDocumento`
- `frontend/app/expedientes/nuevo/page.tsx` — fix redirect to `/expedientes/{id}` + stepper + RFC validation
- `frontend/app/expedientes/[id]/page.tsx` — replace DocumentUploader grid with SmartDropZone + stepper
- `frontend/app/expedientes/[id]/reporte/page.tsx` — ScoreGauge + FactorDetailCard + stepper

---

## Task 1: Backend — legal_refs + factores_detail in evaluation service and API

**Files:**
- Create: `backend/src/domain/scoring/legal_refs.py`
- Modify: `backend/src/services/evaluation_service.py`
- Modify: `backend/src/api/routers/expedientes.py`
- Test: `backend/src/tests/test_evaluation_factores_detail.py`

**Interfaces:**
- Produces: `LEGAL_REFS: dict[str, dict]` used by evaluation_service
- Produces: `evaluar_expediente` now returns `factores_score: dict[str, int]` and `factores_detail: list[dict]`
- Produces: `GET /expedientes/{id}/evaluations/latest` returns `factores_score` and `factores_detail` from summary

- [ ] **Step 1.1: Write the failing tests**

```python
# backend/src/tests/test_evaluation_factores_detail.py
from domain.scoring.legal_refs import LEGAL_REFS

def test_legal_refs_has_sat_69b_definitivo():
    ref = LEGAL_REFS["sat_69b_definitivo"]
    assert ref["category"] == "sat"
    assert "69-B" in ref["ref"]

def test_legal_refs_has_disc_domicilio():
    ref = LEGAL_REFS["disc_domicilio"]
    assert ref["category"] == "discrepancia"
    assert "1.4.14" in ref["ref"]

def test_legal_refs_has_doc_missing():
    ref = LEGAL_REFS["doc_missing"]
    assert ref["category"] == "completitud"

def test_all_known_factor_codes_have_legal_ref():
    known = [
        "sat_69b_definitivo", "sat_69b_presunto", "sat_69b_bis", "sat_69_incumplido",
        "rfc_formato_invalido", "art_49bis_no_verificable",
        "disc_rfc", "disc_razon_social", "disc_domicilio", "disc_representante", "disc_fechas",
        "doc_missing", "doc_expired", "csf_stale", "doc_data_incomplete",
        "manifestacion_incompleta", "socios_incompletos", "rep_legal_incompleto",
    ]
    for code in known:
        assert code in LEGAL_REFS, f"Missing legal_ref for factor_code: {code}"
```

- [ ] **Step 1.2: Run tests — expect FAIL**

```
cd backend && uv run pytest src/tests/test_evaluation_factores_detail.py -v
```
Expected: `ModuleNotFoundError: No module named 'domain.scoring.legal_refs'`

- [ ] **Step 1.3: Create `backend/src/domain/scoring/legal_refs.py`**

```python
LEGAL_REFS: dict[str, dict] = {
    "sat_69b_definitivo": {
        "ref": "Art. 69-B CFF — Listado definitivo de EFOS (Empresas que Facturan Operaciones Simuladas). Operar con un EFOS definitivo invalida los CFDIs emitidos y genera responsabilidad solidaria.",
        "category": "sat",
    },
    "sat_69b_presunto": {
        "ref": "Art. 69-B CFF — Listado presunto EFOS, pendiente de resolución SAT. El contribuyente puede desvirtuar ante el SAT en el plazo legal.",
        "category": "sat",
    },
    "sat_69b_bis": {
        "ref": "Art. 69-B Bis CFF — Transmisión indebida de pérdidas fiscales. El SAT puede rechazar las pérdidas transmitidas y aplicar recargos.",
        "category": "sat",
    },
    "sat_69_incumplido": {
        "ref": "Art. 69 CFF — Contribuyente con obligaciones fiscales incumplidas (créditos firmes, exigibles, CSD sin efectos, no localizados o con sentencia).",
        "category": "sat",
    },
    "rfc_formato_invalido": {
        "ref": "Art. 27 CFF y Resolución Miscelánea Fiscal — El RFC debe cumplir la estructura oficial (3-4 letras + 6 dígitos fecha + 3 homoclave) con dígito verificador válido.",
        "category": "sat",
    },
    "art_49bis_no_verificable": {
        "ref": "Art. 49 Bis CFF (Contrabando técnico) — No existe listado público consultable. Se requiere declaración bajo protesta del contribuyente y revisión manual por el agente aduanal.",
        "category": "sat",
    },
    "disc_rfc": {
        "ref": "Regla 1.4.14 RGCE 2026 — El RFC es el identificador fiscal vinculante. La discrepancia entre documentos indica posible suplantación o error en el expediente.",
        "category": "discrepancia",
    },
    "disc_razon_social": {
        "ref": "Regla 1.4.14 RGCE 2026 — La razón social debe coincidir de forma material en todos los documentos del expediente. Variaciones menores (abreviaturas societarias) son causa de revisión.",
        "category": "discrepancia",
    },
    "disc_domicilio": {
        "ref": "Regla 1.4.14 RGCE 2026 — El domicilio fiscal declarado debe ser consistente entre la CSF, comprobante de domicilio y demás documentos del expediente.",
        "category": "discrepancia",
    },
    "disc_representante": {
        "ref": "Regla 1.4.14 RGCE 2026 — El nombre del representante legal debe coincidir entre el poder notarial, la identificación oficial y el encargo conferido.",
        "category": "discrepancia",
    },
    "disc_fechas": {
        "ref": "Regla 1.4.14 RGCE 2026 — Las fechas de emisión, vigencia y vencimiento de los documentos deben ser congruentes entre sí y con el período evaluado.",
        "category": "discrepancia",
    },
    "doc_missing": {
        "ref": "Regla 1.4.14 RGCE 2026 — La documentación completa es requisito para inscribirse y operar en el Padrón de Importadores/Exportadores.",
        "category": "completitud",
    },
    "doc_expired": {
        "ref": "Regla 1.4.14 RGCE 2026 — El comprobante de domicilio tiene vigencia máxima de 90 días naturales a partir de su fecha de emisión.",
        "category": "completitud",
    },
    "csf_stale": {
        "ref": "SAT / Regla 1.4.14 RGCE 2026 — La Constancia de Situación Fiscal debe corresponder al mes calendario en curso para acreditar la situación fiscal vigente.",
        "category": "completitud",
    },
    "doc_data_incomplete": {
        "ref": "Regla 1.4.14 RGCE 2026 — Todos los campos obligatorios del documento deben estar capturados y verificados para que el expediente sea evaluable.",
        "category": "completitud",
    },
    "manifestacion_incompleta": {
        "ref": "Regla 1.4.14 RGCE 2026 — La Manifestación bajo Protesta de Decir Verdad debe incluir la cláusula explícita de no encontrarse en los listados del Art. 69-B y Art. 49 Bis CFF.",
        "category": "completitud",
    },
    "socios_incompletos": {
        "ref": "Regla 1.4.14 RGCE 2026 y LFPIORPI — Se requiere identificar a todos los socios, accionistas y beneficiario controlador del acta constitutiva para cumplir con los controles antilavado.",
        "category": "completitud",
    },
    "rep_legal_incompleto": {
        "ref": "Regla 1.4.14 RGCE 2026 — El nombre completo del representante legal debe capturarse desde la identificación oficial para vincularlo con el poder notarial y el encargo conferido.",
        "category": "completitud",
    },
}
```

- [ ] **Step 1.4: Run tests — expect PASS**

```
cd backend && uv run pytest src/tests/test_evaluation_factores_detail.py -v
```
Expected: 4 tests PASS

- [ ] **Step 1.5: Update `backend/src/services/evaluation_service.py`**

Replace the entire file:

```python
from datetime import date, datetime, timezone
from domain.scoring.factors import factores_listas_sat, factores_discrepancias, factores_completitud
from domain.scoring.engine import evaluar
from domain.scoring.lifecycle import necesita_actualizacion
from domain.scoring.acciones import acciones_para
from domain.scoring.legal_refs import LEGAL_REFS
from infrastructure.sat.lookup import consultar_rfc_en_listas

def evaluar_expediente(supabase_client, expediente_id: str, resultado_reconciliacion, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    expediente = supabase_client.table("expedientes").select("*").eq("id", expediente_id).execute().data[0]
    documentos = supabase_client.table("documentos").select("*").eq("expediente_id", expediente_id).execute().data
    socios = supabase_client.table("socios").select("*").eq("expediente_id", expediente_id).execute().data

    sat_hits = consultar_rfc_en_listas(supabase_client, expediente_id, expediente["rfc"])
    factores = factores_listas_sat(sat_hits) + factores_discrepancias(resultado_reconciliacion) + factores_completitud(documentos, socios, hoy)
    resultado = evaluar(factores)
    acciones = acciones_para([f.factor_code for f in resultado.factores])
    needs_update = necesita_actualizacion(documentos, None, hoy, cliente_reporto_cambio=False)

    factores_score = {f.factor_code: f.points for f in resultado.factores}
    factores_detail = [
        {
            "factor_code": f.factor_code,
            "points": f.points,
            "is_critical_block": f.is_critical_block,
            "detail": f.detail,
            "evidence": f.evidence,
            "legal_ref": LEGAL_REFS.get(f.factor_code, {}).get("ref", ""),
            "category": LEGAL_REFS.get(f.factor_code, {}).get("category", "otro"),
        }
        for f in resultado.factores
    ]

    supabase_client.table("evaluations").insert({
        "expediente_id": expediente_id,
        "score_total": resultado.score_total,
        "decision": resultado.decision,
        "critical_blocks": resultado.critical_blocks,
        "summary": {
            "acciones_sugeridas": acciones,
            "factores_score": factores_score,
            "factores_detail": factores_detail,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    supabase_client.table("expedientes").update({
        "decision": resultado.decision,
        "score_total": resultado.score_total,
        "status": "needs_update" if needs_update else "completed",
        "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", expediente_id).execute()

    return {
        "score_total": resultado.score_total,
        "decision": resultado.decision,
        "factores_score": factores_score,
        "factores_detail": factores_detail,
        "acciones_sugeridas": acciones,
        "needs_update": needs_update,
    }
```

- [ ] **Step 1.6: Fix `get_latest_evaluation` in `backend/src/api/routers/expedientes.py`**

Replace only the `get_latest_evaluation` function (lines 44–63):

```python
@router.get("/{expediente_id}/evaluations/latest")
def get_latest_evaluation(expediente_id: str, supabase: Client = Depends(get_supabase_client)):
    result = (
        supabase.table("evaluations")
        .select("*")
        .eq("expediente_id", expediente_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    summary = row.get("summary") or {}
    return {
        "decision": row["decision"],
        "score_total": row["score_total"],
        "factores_score": summary.get("factores_score", {}),
        "factores_detail": summary.get("factores_detail", []),
        "acciones_sugeridas": summary.get("acciones_sugeridas", []),
        "evaluated_at": row["created_at"],
    }
```

- [ ] **Step 1.7: Verify existing tests pass**

```
cd backend && uv run pytest src/tests/ -v --tb=short
```
Expected: all tests PASS including the 4 new ones

- [ ] **Step 1.8: Commit**

```bash
git add backend/src/domain/scoring/legal_refs.py backend/src/services/evaluation_service.py backend/src/api/routers/expedientes.py backend/src/tests/test_evaluation_factores_detail.py
git commit -m "feat: expose factores_detail with legal refs in evaluation API"
```

---

## Task 2: Backend — classify endpoint

**Files:**
- Modify: `backend/src/infrastructure/ai/pdf.py` — add `extraer_texto_de_bytes`
- Create: `backend/src/infrastructure/ai/classify.py`
- Modify: `backend/src/api/routers/documentos.py` — add `POST /documentos/classify`
- Test: `backend/src/tests/test_classify.py`

**Interfaces:**
- Consumes: `get_groq_model()` from `infrastructure.ai.groq_client`
- Produces: `clasificar_documento(texto: str) -> {"doc_type": str, "confidence": "high"|"low"}`
- Produces: `extraer_texto_de_bytes(content: bytes) -> str`
- Produces: `POST /documentos/classify` multipart → `{"doc_type": str, "confidence": str, "suggested_label": str}`

- [ ] **Step 2.1: Write the failing tests**

```python
# backend/src/tests/test_classify.py
from unittest.mock import patch, MagicMock
from infrastructure.ai.classify import clasificar_documento

VALID_DOC_TYPES = {
    "csf", "acta_constitutiva", "comprobante_domicilio",
    "identificacion_rep_legal", "poder_notarial",
    "encargo_conferido", "manifestacion_protesta",
}

def test_clasificar_documento_returns_valid_doc_type():
    texto = "Constancia de Situación Fiscal\nServicio de Administración Tributaria\nRFC: EKU9003173C9"
    mock_response = MagicMock()
    mock_response.content = '{"doc_type": "csf", "confidence": "high"}'
    with patch("infrastructure.ai.classify.get_groq_model") as mock_model_fn:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_model_fn.return_value = mock_llm
        result = clasificar_documento(texto)
    assert result["doc_type"] in VALID_DOC_TYPES
    assert result["confidence"] in ("high", "low")

def test_clasificar_documento_falls_back_on_bad_json():
    mock_response = MagicMock()
    mock_response.content = "not valid json at all"
    with patch("infrastructure.ai.classify.get_groq_model") as mock_model_fn:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_model_fn.return_value = mock_llm
        result = clasificar_documento("some text")
    assert result["doc_type"] == "unknown"
    assert result["confidence"] == "low"
```

- [ ] **Step 2.2: Run tests — expect FAIL**

```
cd backend && uv run pytest src/tests/test_classify.py -v
```
Expected: `ModuleNotFoundError: No module named 'infrastructure.ai.classify'`

- [ ] **Step 2.3: Add `extraer_texto_de_bytes` to `backend/src/infrastructure/ai/pdf.py`**

Read the current file first, then append at the bottom:

```python
import io

def extraer_texto_de_bytes(content: bytes) -> str:
    """Extract selectable text from PDF bytes without touching storage."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""
```

- [ ] **Step 2.4: Create `backend/src/infrastructure/ai/classify.py`**

```python
import json
from langchain_core.messages import HumanMessage
from infrastructure.ai.groq_client import get_groq_model

VALID_DOC_TYPES = {
    "csf", "acta_constitutiva", "comprobante_domicilio",
    "identificacion_rep_legal", "poder_notarial",
    "encargo_conferido", "manifestacion_protesta",
}

_PROMPT = """You are a document classification assistant for a Mexican customs agency KYB system.
Read the following document text and identify its type.

Document types:
- csf: Constancia de Situación Fiscal (SAT tax status certificate)
- acta_constitutiva: Acta Constitutiva (articles of incorporation)
- comprobante_domicilio: Comprobante de Domicilio (proof of address — CFE, Telmex, water, etc.)
- identificacion_rep_legal: Identificación Oficial del Representante Legal (INE, pasaporte)
- poder_notarial: Poder Notarial (notarial power of attorney)
- encargo_conferido: Encargo Conferido (customs agent authorization letter, patente aduanal)
- manifestacion_protesta: Manifestación bajo Protesta de Decir Verdad (Regla 1.4.14 declaration)

Return ONLY valid JSON with no extra text:
{{"doc_type": "<one of the types above or 'unknown'>", "confidence": "<high or low>"}}

Use "high" confidence when the document clearly matches one type.
Use "low" when unsure.

Document text (first 2000 chars):
{text}"""


def clasificar_documento(texto: str) -> dict:
    """Classify a document by its text content. Returns {doc_type, confidence}."""
    try:
        llm = get_groq_model()
        prompt = _PROMPT.format(text=texto[:2000])
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        doc_type = data.get("doc_type", "unknown")
        confidence = data.get("confidence", "low")
        if doc_type not in VALID_DOC_TYPES:
            doc_type = "unknown"
            confidence = "low"
        return {"doc_type": doc_type, "confidence": confidence}
    except Exception:
        return {"doc_type": "unknown", "confidence": "low"}
```

- [ ] **Step 2.5: Run tests — expect PASS**

```
cd backend && uv run pytest src/tests/test_classify.py -v
```
Expected: 2 tests PASS

- [ ] **Step 2.6: Add `POST /documentos/classify` to `backend/src/api/routers/documentos.py`**

Add these imports after the existing imports at the top:

```python
from fastapi import UploadFile, File
from infrastructure.ai.pdf import extraer_texto_de_bytes
from infrastructure.ai.classify import clasificar_documento
```

Add this endpoint at the end of the file:

```python
@router.post("/classify")
async def classify_documento(file: UploadFile = File(...)):
    """Classify a PDF by content without creating a DB record."""
    content = await file.read()
    texto = extraer_texto_de_bytes(content)
    if not texto.strip():
        return {"doc_type": "unknown", "confidence": "low", "suggested_label": "Sin texto extraído"}
    result = clasificar_documento(texto)
    labels = {
        "csf": "Constancia de Situación Fiscal",
        "acta_constitutiva": "Acta Constitutiva",
        "comprobante_domicilio": "Comprobante de Domicilio",
        "identificacion_rep_legal": "ID Representante Legal",
        "poder_notarial": "Poder Notarial",
        "encargo_conferido": "Encargo Conferido",
        "manifestacion_protesta": "Manifestación bajo Protesta",
        "unknown": "Sin clasificar",
    }
    return {
        "doc_type": result["doc_type"],
        "confidence": result["confidence"],
        "suggested_label": labels.get(result["doc_type"], "Sin clasificar"),
    }
```

- [ ] **Step 2.7: Smoke test the endpoint**

```
cd backend && uv run fastapi dev src/main.py
```

In a second terminal:
```bash
curl -X POST http://localhost:8000/documentos/classify \
  -F "file=@scripts/demo_pdfs/expediente_1_safe/csf.pdf"
```
Expected: `{"doc_type":"csf","confidence":"high","suggested_label":"Constancia de Situación Fiscal"}`

- [ ] **Step 2.8: Run all backend tests**

```
cd backend && uv run pytest src/tests/ -v --tb=short
```
Expected: all tests PASS

- [ ] **Step 2.9: Commit**

```bash
git add backend/src/infrastructure/ai/classify.py backend/src/infrastructure/ai/pdf.py backend/src/api/routers/documentos.py backend/src/tests/test_classify.py
git commit -m "feat: add POST /documentos/classify for AI content-based doc classification"
```

---

## Task 3: Frontend — api-client types + classifyDocumento

**Files:**
- Modify: `frontend/lib/api-client.ts`

**Interfaces:**
- Produces: `FactorDetail` type — used by Tasks 5 and 9
- Produces: `ClassifyResult` type — used by Task 6
- Produces: `api.classifyDocumento(file: File): Promise<ClassifyResult>` — used by Task 6
- Updates: `EvaluationResult` adds `factores_detail: FactorDetail[]`

- [ ] **Step 3.1: Replace `frontend/lib/api-client.ts` entirely**

```typescript
const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
const API_URL = RAW_API_URL.replace(/\/+$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export type Decision = "safe" | "review_required" | "high_risk";

export type Expediente = {
  id: string;
  razon_social: string;
  rfc: string;
  status: string;
  decision: Decision | null;
  score_total: number | null;
  domicilio_fiscal?: string;
  representante_legal?: string;
};

export type Documento = {
  id: string;
  expediente_id: string;
  doc_type: string;
  entry_method: "uploaded" | "manual";
  extraction_status:
    | "pending"
    | "processing"
    | "extracted"
    | "human_reviewed"
    | "not_applicable"
    | "error";
  fields: Record<string, unknown>;
  human_reviewed: boolean;
  storage_path?: string | null;
};

export type FactorDetail = {
  factor_code: string;
  points: number;
  is_critical_block: boolean;
  detail: string;
  evidence: Record<string, unknown> | null;
  legal_ref: string;
  category: "sat" | "discrepancia" | "completitud" | "otro";
};

export type EvaluationResult = {
  decision: Decision;
  score_total: number;
  factores_score: Record<string, number>;
  factores_detail: FactorDetail[];
  acciones_sugeridas: string[];
  evaluated_at: string;
};

export type ClassifyResult = {
  doc_type: string;
  confidence: "high" | "low";
  suggested_label: string;
};

export type SatImportRun = {
  id: string;
  list_type: string;
  status: string;
  rows_imported: number | null;
  started_at: string;
  finished_at: string | null;
};

export const api = {
  checkHealth: (): Promise<{ status: string }> =>
    request("/health"),

  listExpedientes: (): Promise<Expediente[]> =>
    request("/expedientes"),

  getExpediente: (id: string): Promise<Expediente> =>
    request(`/expedientes/${id}`),

  createExpediente: (data: {
    razon_social: string;
    rfc: string;
    domicilio_fiscal?: string;
    representante_legal?: string;
  }): Promise<Expediente> =>
    request("/expedientes", { method: "POST", body: JSON.stringify(data) }),

  evaluate: (id: string): Promise<EvaluationResult> =>
    request(`/expedientes/${id}/evaluate`, { method: "POST" }),

  getLatestEvaluation: (id: string): Promise<EvaluationResult | null> =>
    request(`/expedientes/${id}/evaluations/latest`),

  listDocumentos: (expedienteId: string): Promise<Documento[]> =>
    request(`/documentos?expediente_id=${expedienteId}`),

  getDocumento: async (
    expedienteId: string,
    documentoId: string
  ): Promise<Documento | null> => {
    const docs = await request<Documento[]>(
      `/documentos?expediente_id=${expedienteId}`
    );
    return docs.find((d) => d.id === documentoId) ?? null;
  },

  crearDocumento: (
    expedienteId: string,
    docType: string,
    entryMethod: "uploaded" | "manual"
  ): Promise<{ documento_id: string; signed_url?: string }> =>
    request("/documentos", {
      method: "POST",
      body: JSON.stringify({
        expediente_id: expedienteId,
        doc_type: docType,
        entry_method: entryMethod,
      }),
    }),

  extractDocumento: (documentoId: string): Promise<Documento> =>
    request(`/documentos/${documentoId}/extract`, { method: "POST" }),

  reviewDocumento: (
    id: string,
    fields: Record<string, unknown>
  ): Promise<Documento> =>
    request(`/documentos/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ fields }),
    }),

  classifyDocumento: async (file: File): Promise<ClassifyResult> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/documentos/classify`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`Classify error ${res.status}`);
    return res.json();
  },

  reportChange: (id: string, reason: string): Promise<void> =>
    request(`/expedientes/${id}/report-change`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  triggerSatImport: (listType: string): Promise<SatImportRun> =>
    request(`/admin/ingest/${listType}`, { method: "POST" }),

  listSatImportRuns: (): Promise<SatImportRun[]> =>
    request("/admin/sat-import-runs"),

  listConsultasSat: (expedienteId: string): Promise<unknown[]> =>
    request(`/expedientes/${expedienteId}/consultas-sat`),
};

export async function checkHealth(): Promise<{ status: string }> {
  return api.checkHealth();
}
```

- [ ] **Step 3.2: Verify TypeScript compiles**

```
cd frontend && pnpm build 2>&1 | head -30
```
Expected: no TypeScript errors related to `api-client.ts`

- [ ] **Step 3.3: Commit**

```bash
git add frontend/lib/api-client.ts
git commit -m "feat: add FactorDetail, ClassifyResult types and classifyDocumento to api-client"
```

---

## Task 4: Frontend — StepperHeader + ScoreGauge components

**Files:**
- Create: `frontend/components/StepperHeader.tsx`
- Create: `frontend/components/ScoreGauge.tsx`

**Interfaces:**
- `StepperHeader` props: `{ currentStep: 1 | 2 | 3 | 4 }`
- `ScoreGauge` props: `{ score: number; decision: string }`

- [ ] **Step 4.1: Create `frontend/components/StepperHeader.tsx`**

```tsx
const STEPS = [
  { n: 1, label: "Datos empresa" },
  { n: 2, label: "Documentos" },
  { n: 3, label: "Revisión" },
  { n: 4, label: "Reporte KYB" },
] as const;

export function StepperHeader({ currentStep }: { currentStep: 1 | 2 | 3 | 4 }) {
  return (
    <nav className="flex items-center gap-0 mb-8">
      {STEPS.map((step, i) => {
        const done = step.n < currentStep;
        const active = step.n === currentStep;
        return (
          <div key={step.n} className="flex items-center gap-0 flex-1 min-w-0">
            <div className="flex flex-col items-center gap-1 shrink-0">
              <div
                className={[
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-colors",
                  done
                    ? "bg-primary border-primary text-primary-foreground"
                    : active
                    ? "border-primary text-primary bg-primary/10"
                    : "border-border text-muted-foreground bg-card",
                ].join(" ")}
              >
                {done ? "✓" : step.n}
              </div>
              <span
                className={[
                  "text-xs whitespace-nowrap",
                  active ? "text-primary font-medium" : "text-muted-foreground",
                ].join(" ")}
              >
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={[
                  "flex-1 h-px mx-2 mt-[-12px]",
                  done ? "bg-primary" : "bg-border",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 4.2: Create `frontend/components/ScoreGauge.tsx`**

```tsx
type Decision = "safe" | "review_required" | "high_risk";

const DECISION_CONFIG: Record<Decision, { label: string; color: string; textClass: string }> = {
  safe: { label: "Aprobado", color: "bg-success", textClass: "text-success" },
  review_required: { label: "Requiere revisión", color: "bg-warning", textClass: "text-warning" },
  high_risk: { label: "Alto riesgo", color: "bg-destructive", textClass: "text-destructive" },
};

export function ScoreGauge({ score, decision }: { score: number; decision: string }) {
  const config = DECISION_CONFIG[decision as Decision] ?? DECISION_CONFIG.high_risk;
  const pct = Math.min(Math.max(score, 0), 100);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Score de riesgo</p>
          <p className={`text-5xl font-bold leading-none ${config.textClass}`}>
            {score}
            <span className="text-lg font-normal text-muted-foreground ml-1">/ 100</span>
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Decisión</p>
          <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${config.color} text-background`}>
            {config.label}
          </span>
        </div>
      </div>

      <div className="relative h-3 rounded-full overflow-hidden bg-muted">
        <div className="absolute inset-0 flex">
          <div className="bg-success/30" style={{ width: "30%" }} />
          <div className="bg-warning/30" style={{ width: "40%" }} />
          <div className="bg-destructive/30" style={{ width: "30%" }} />
        </div>
        <div
          className={`absolute top-0 left-0 h-full rounded-full transition-all duration-500 ${config.color}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>0 — Sin riesgo</span>
        <span>30 — Revisión</span>
        <span>70+ — Alto riesgo</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4.3: Verify compile**

```
cd frontend && pnpm build 2>&1 | grep -i error | head -10
```
Expected: no errors

- [ ] **Step 4.4: Commit**

```bash
git add frontend/components/StepperHeader.tsx frontend/components/ScoreGauge.tsx
git commit -m "feat: add StepperHeader and ScoreGauge components"
```

---

## Task 5: Frontend — FactorDetailCard component

**Files:**
- Create: `frontend/components/FactorDetailCard.tsx`

**Interfaces:**
- Consumes: `FactorDetail` from `@/lib/api-client`
- Props: `{ factor: FactorDetail; maxPoints: number }`

- [ ] **Step 5.1: Create `frontend/components/FactorDetailCard.tsx`**

```tsx
import type { FactorDetail } from "@/lib/api-client";

const FACTOR_LABELS: Record<string, string> = {
  sat_69b_definitivo: "EFOS Definitivo (Art. 69-B CFF)",
  sat_69b_presunto: "EFOS Presunto (Art. 69-B CFF)",
  sat_69b_bis: "Pérdidas fiscales indebidas (Art. 69-B Bis CFF)",
  sat_69_incumplido: "Contribuyente incumplido (Art. 69 CFF)",
  rfc_formato_invalido: "RFC con formato inválido",
  art_49bis_no_verificable: "Art. 49 Bis CFF — sin lista pública verificable",
  disc_rfc: "Discrepancia de RFC entre documentos",
  disc_razon_social: "Discrepancia de razón social",
  disc_domicilio: "Discrepancia de domicilio fiscal",
  disc_representante: "Discrepancia del representante legal",
  disc_fechas: "Inconsistencia de fechas",
  doc_missing: "Documento requerido faltante",
  doc_expired: "Comprobante de domicilio vencido (>90 días)",
  csf_stale: "Constancia de Situación Fiscal desactualizada",
  doc_data_incomplete: "Campos obligatorios incompletos en documento",
  manifestacion_incompleta: "Manifestación bajo protesta incompleta",
  socios_incompletos: "Socios / beneficiario controlador no registrados",
  rep_legal_incompleto: "Representante legal sin nombre completo",
};

const CATEGORY_CHIP: Record<string, { label: string; className: string }> = {
  sat: { label: "SAT", className: "bg-destructive/15 text-destructive" },
  discrepancia: { label: "Discrepancia", className: "bg-warning/15 text-warning" },
  completitud: { label: "Completitud", className: "bg-primary/15 text-primary" },
  otro: { label: "Otro", className: "bg-muted text-muted-foreground" },
};

export function FactorDetailCard({
  factor,
  maxPoints,
}: {
  factor: FactorDetail;
  maxPoints: number;
}) {
  const chip = CATEGORY_CHIP[factor.category] ?? CATEGORY_CHIP.otro;
  const label = FACTOR_LABELS[factor.factor_code] ?? factor.factor_code;
  const barPct = maxPoints > 0 ? Math.round((factor.points / maxPoints) * 100) : 0;
  const isCritical = factor.is_critical_block;

  return (
    <div
      className={[
        "rounded-xl border p-4 space-y-3 transition-colors",
        isCritical
          ? "border-destructive/50 bg-destructive/5"
          : factor.points > 0
          ? "border-warning/30 bg-card"
          : "border-border bg-card/50",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {isCritical && (
              <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-destructive text-background">
                BLOQUEO CRÍTICO
              </span>
            )}
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${chip.className}`}>
              {chip.label}
            </span>
          </div>
          <p className="text-sm font-semibold leading-snug">{label}</p>
        </div>
        <div className="shrink-0 text-right">
          <p
            className={`text-2xl font-bold leading-none ${
              isCritical ? "text-destructive" : factor.points > 0 ? "text-warning" : "text-success"
            }`}
          >
            {factor.points > 0 ? `+${factor.points}` : "0"}
          </p>
          <p className="text-xs text-muted-foreground">puntos</p>
        </div>
      </div>

      {factor.points > 0 && (
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full ${isCritical ? "bg-destructive" : "bg-warning"}`}
            style={{ width: `${barPct}%` }}
          />
        </div>
      )}

      <p className="text-sm text-foreground/90 leading-relaxed">{factor.detail}</p>

      {factor.legal_ref && (
        <div className="flex items-start gap-2 rounded-lg bg-muted/60 px-3 py-2">
          <span className="text-muted-foreground mt-0.5 shrink-0 text-xs">§</span>
          <p className="text-xs text-muted-foreground leading-relaxed">{factor.legal_ref}</p>
        </div>
      )}

      {factor.evidence && Object.keys(factor.evidence).length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer hover:text-foreground transition-colors">
            Ver evidencia técnica
          </summary>
          <pre className="mt-1 rounded bg-muted px-2 py-1 text-xs overflow-auto">
            {JSON.stringify(factor.evidence, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
```

- [ ] **Step 5.2: Verify compile**

```
cd frontend && pnpm build 2>&1 | grep -i error | head -10
```
Expected: no errors

- [ ] **Step 5.3: Commit**

```bash
git add frontend/components/FactorDetailCard.tsx
git commit -m "feat: add FactorDetailCard with legal reference and evidence display"
```

---

## Task 6: Frontend — SmartDropZone component

**Files:**
- Create: `frontend/components/SmartDropZone.tsx`

**Interfaces:**
- Consumes: `api.classifyDocumento(file: File): Promise<ClassifyResult>` from `@/lib/api-client`
- Consumes: `api.crearDocumento`, `api.extractDocumento` from `@/lib/api-client`
- Props: `{ expedienteId: string; existingDocTypes: string[]; onAllDone: () => void }`

- [ ] **Step 6.1: Create `frontend/components/SmartDropZone.tsx`**

```tsx
"use client";
import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

const DOC_TYPE_OPTIONS = [
  { value: "csf", label: "Constancia de Situación Fiscal" },
  { value: "acta_constitutiva", label: "Acta Constitutiva" },
  { value: "comprobante_domicilio", label: "Comprobante de Domicilio" },
  { value: "identificacion_rep_legal", label: "ID Representante Legal" },
  { value: "poder_notarial", label: "Poder Notarial" },
  { value: "encargo_conferido", label: "Encargo Conferido" },
  { value: "manifestacion_protesta", label: "Manifestación bajo Protesta" },
];

type FileState = {
  file: File;
  status: "classifying" | "classified" | "uploading" | "extracting" | "done" | "error";
  docType: string;
  confidence: "high" | "low";
  suggestedLabel: string;
  errorMsg?: string;
};

type Props = {
  expedienteId: string;
  existingDocTypes: string[];
  onAllDone: () => void;
};

export function SmartDropZone({ expedienteId, existingDocTypes, onAllDone }: Props) {
  const [files, setFiles] = useState<FileState[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const classifyFiles = useCallback(async (newFiles: File[]) => {
    const pdfs = newFiles.filter(
      (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
    );
    if (!pdfs.length) return;

    const pending: FileState[] = pdfs.map((f) => ({
      file: f,
      status: "classifying",
      docType: "unknown",
      confidence: "low",
      suggestedLabel: "Clasificando…",
    }));

    setFiles((prev) => {
      const startIdx = prev.length;
      const updated = [...prev, ...pending];
      // Kick off classification after state is set
      Promise.all(
        pdfs.map((f) =>
          api.classifyDocumento(f).catch(() => ({
            doc_type: "unknown" as const,
            confidence: "low" as const,
            suggested_label: "Sin clasificar",
          }))
        )
      ).then((results) => {
        setFiles((current) => {
          const next = [...current];
          results.forEach((result, i) => {
            next[startIdx + i] = {
              ...next[startIdx + i],
              status: "classified",
              docType: result.doc_type,
              confidence: result.confidence,
              suggestedLabel: result.suggested_label,
            };
          });
          return next;
        });
      });
      return updated;
    });
  }, []);

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    classifyFiles(Array.from(e.dataTransfer.files));
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      classifyFiles(Array.from(e.target.files));
      e.target.value = "";
    }
  }

  function setDocType(idx: number, docType: string) {
    const label = DOC_TYPE_OPTIONS.find((o) => o.value === docType)?.label ?? "Sin clasificar";
    setFiles((prev) =>
      prev.map((f, i) =>
        i === idx ? { ...f, docType, suggestedLabel: label, confidence: "high" } : f
      )
    );
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  async function processAll() {
    const toProcess = files
      .map((f, i) => ({ ...f, idx: i }))
      .filter((f) => f.status === "classified" && f.docType !== "unknown");

    if (!toProcess.length) return;
    setProcessing(true);

    await Promise.all(
      toProcess.map(async ({ file, docType, idx }) => {
        const update = (status: FileState["status"], errorMsg?: string) =>
          setFiles((prev) =>
            prev.map((f, i) => (i === idx ? { ...f, status, errorMsg } : f))
          );

        try {
          update("uploading");
          const { documento_id, signed_url } = await api.crearDocumento(
            expedienteId,
            docType,
            "uploaded"
          );
          if (signed_url) {
            await fetch(signed_url, { method: "PUT", body: file });
          }
          update("extracting");
          await api.extractDocumento(documento_id);
          update("done");
        } catch (err) {
          update("error", err instanceof Error ? err.message : "Error al procesar");
        }
      })
    );

    setProcessing(false);
    const allDone = files.every(
      (f) => f.status === "done" || f.status === "error" || f.docType === "unknown"
    );
    if (allDone) onAllDone();
  }

  const readyToProcess = files.some(
    (f) => f.status === "classified" && f.docType !== "unknown"
  );
  const allProcessed =
    files.length > 0 &&
    files.every((f) => f.status === "done" || f.status === "error");

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={[
          "rounded-xl border-2 border-dashed cursor-pointer transition-all p-10 text-center space-y-2 select-none",
          isDragging
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border hover:border-primary/50 hover:bg-muted/30",
        ].join(" ")}
      >
        <div className="text-4xl">📂</div>
        <p className="font-medium text-sm">
          Arrastrá tus PDFs aquí, o hacé clic para seleccionar
        </p>
        <p className="text-xs text-muted-foreground">
          Podés soltar varios archivos a la vez — la IA los clasifica automáticamente por contenido
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="hidden"
          onChange={onInputChange}
        />
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f, idx) => (
            <div
              key={idx}
              className={[
                "rounded-lg border p-3 flex items-center gap-3 text-sm",
                f.status === "done"
                  ? "border-success/40 bg-success/5"
                  : f.status === "error"
                  ? "border-destructive/40 bg-destructive/5"
                  : "border-border bg-card",
              ].join(" ")}
            >
              <span className="text-base shrink-0 w-5 text-center">
                {f.status === "done"
                  ? "✓"
                  : f.status === "error"
                  ? "✗"
                  : f.status === "classifying" || f.status === "uploading" || f.status === "extracting"
                  ? "⟳"
                  : f.confidence === "high"
                  ? "✓"
                  : "⚠"}
              </span>

              <span className="font-mono text-xs text-muted-foreground truncate min-w-0 flex-1">
                {f.file.name}
              </span>

              {f.status === "classified" ? (
                <select
                  value={f.docType}
                  onChange={(e) => setDocType(idx, e.target.value)}
                  className="text-xs rounded-md border border-border bg-background px-2 py-1 shrink-0"
                >
                  <option value="unknown">Sin clasificar</option>
                  {DOC_TYPE_OPTIONS.filter(
                    (o) => !existingDocTypes.includes(o.value) || o.value === f.docType
                  ).map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : (
                <span
                  className={[
                    "text-xs shrink-0",
                    f.status === "done"
                      ? "text-success"
                      : f.status === "error"
                      ? "text-destructive"
                      : "text-muted-foreground animate-pulse",
                  ].join(" ")}
                >
                  {f.status === "error"
                    ? f.errorMsg
                    : f.status === "classifying"
                    ? "Clasificando con IA…"
                    : f.status === "uploading"
                    ? "Subiendo…"
                    : f.status === "extracting"
                    ? "Extrayendo campos con IA…"
                    : f.status === "done"
                    ? "Listo ✓"
                    : ""}
                </span>
              )}

              {(f.status === "classified" || f.status === "error") && (
                <button
                  onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                  className="text-muted-foreground hover:text-foreground shrink-0 text-xs ml-1"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Process button */}
      {files.length > 0 && !allProcessed && (
        <Button
          onClick={processAll}
          disabled={!readyToProcess || processing}
          className="w-full bg-primary text-primary-foreground"
        >
          {processing ? "Procesando documentos…" : "Procesar todos los documentos"}
        </Button>
      )}

      {/* Done state */}
      {allProcessed && (
        <div className="rounded-xl border border-success/40 bg-success/5 p-4 text-center space-y-2">
          <p className="text-sm font-medium text-success">✓ Todos los documentos procesados</p>
          <p className="text-xs text-muted-foreground">
            Revisá los campos extraídos en cada documento, luego ejecutá la evaluación KYB.
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 6.2: Verify compile**

```
cd frontend && pnpm build 2>&1 | grep -i error | head -10
```
Expected: no errors

- [ ] **Step 6.3: Commit**

```bash
git add frontend/components/SmartDropZone.tsx
git commit -m "feat: add SmartDropZone with AI content-based classification and parallel upload"
```

---

## Task 7: Frontend — Fix nuevo/page.tsx

**Files:**
- Modify: `frontend/app/expedientes/nuevo/page.tsx`

**Critical fix:** On success, redirect to `/expedientes/${expediente.id}` NOT `/expedientes/${expediente.id}/reporte`.

- [ ] **Step 7.1: Replace `frontend/app/expedientes/nuevo/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { StepperHeader } from "@/components/StepperHeader";

const RFC_REGEX = /^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$/;

export default function NuevoExpedientePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    razon_social: "",
    rfc: "",
    domicilio_fiscal: "",
    representante_legal: "",
  });
  const [rfcError, setRfcError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function validateRfc(value: string): string | null {
    if (!value) return null;
    if (!RFC_REGEX.test(value))
      return "RFC inválido. Formato: 3-4 letras + 6 dígitos fecha + 3 caracteres homoclave (ej: EKU9003173C9)";
    return null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const rfcErr = validateRfc(form.rfc);
    if (rfcErr) { setRfcError(rfcErr); return; }
    setLoading(true);
    setError(null);
    try {
      const expediente = await api.createExpediente(form);
      router.push(`/expedientes/${expediente.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear expediente");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-lg mx-auto">
        <StepperHeader currentStep={1} />

        <div className="mb-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">
            ← Volver al dashboard
          </Link>
          <h1 className="text-2xl font-bold mt-2">Datos de la empresa</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Ingresá los datos básicos del cliente para iniciar el expediente KYB.
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <Label htmlFor="razon_social">
              Razón social <span className="text-destructive">*</span>
            </Label>
            <Input
              id="razon_social"
              placeholder="Ej: Empresa Ejemplo SA de CV"
              value={form.razon_social}
              onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
              required
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="rfc">
              RFC <span className="text-destructive">*</span>
            </Label>
            <Input
              id="rfc"
              placeholder="Ej: EKU9003173C9"
              value={form.rfc}
              onChange={(e) => {
                const val = e.target.value.toUpperCase();
                setForm({ ...form, rfc: val });
                setRfcError(validateRfc(val));
              }}
              required
              className={`mt-1 font-mono ${rfcError ? "border-destructive" : ""}`}
            />
            {rfcError && <p className="text-destructive text-xs mt-1">{rfcErr}</p>}
            {form.rfc && !rfcError && (
              <p className="text-success text-xs mt-1">✓ Formato RFC válido</p>
            )}
          </div>

          <div>
            <Label htmlFor="domicilio_fiscal">Domicilio fiscal</Label>
            <Input
              id="domicilio_fiscal"
              placeholder="Ej: Av. Insurgentes Sur 123, Col. Roma, CDMX"
              value={form.domicilio_fiscal}
              onChange={(e) => setForm({ ...form, domicilio_fiscal: e.target.value })}
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="representante_legal">Representante legal</Label>
            <Input
              id="representante_legal"
              placeholder="Ej: Juan Pérez García"
              value={form.representante_legal}
              onChange={(e) => setForm({ ...form, representante_legal: e.target.value })}
              className="mt-1"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2">
              <p className="text-destructive text-sm">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            disabled={loading || !!rfcError}
            className="w-full bg-primary text-primary-foreground"
          >
            {loading ? "Creando expediente…" : "Continuar — Cargar documentos →"}
          </Button>
        </form>
      </div>
    </main>
  );
}
```

**NOTE:** There is a typo in the JSX above — `{rfcErr}` should be `{rfcError}`. The corrected line is:
```tsx
{rfcError && <p className="text-destructive text-xs mt-1">{rfcError}</p>}
```

- [ ] **Step 7.2: Verify locally**

```
cd frontend && pnpm dev
```
Open `http://localhost:3000/expedientes/nuevo`. Verify:
- Stepper shows Step 1 active
- RFC field shows green checkmark or red error inline as you type
- After submit, browser navigates to `/expedientes/{id}` (NOT `/reporte`)

- [ ] **Step 7.3: Commit**

```bash
git add frontend/app/expedientes/nuevo/page.tsx
git commit -m "feat: fix nuevo expediente redirect + stepper + inline RFC validation"
```

---

## Task 8: Frontend — Update expediente detail page

**Files:**
- Modify: `frontend/app/expedientes/[id]/page.tsx`

**Interfaces:**
- Consumes: `SmartDropZone` (Task 6), `StepperHeader` (Task 4)
- Removes dependency on `DocumentUploader` (kept in codebase but no longer rendered here)

- [ ] **Step 8.1: Replace `frontend/app/expedientes/[id]/page.tsx`**

```tsx
import Link from "next/link";
import { api } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SmartDropZone } from "@/components/SmartDropZone";
import { StepperHeader } from "@/components/StepperHeader";

const DOC_TYPE_LABELS: Record<string, string> = {
  csf: "Constancia de Situación Fiscal",
  acta_constitutiva: "Acta Constitutiva",
  comprobante_domicilio: "Comprobante de Domicilio",
  identificacion_rep_legal: "ID Representante Legal",
  poder_notarial: "Poder Notarial",
  encargo_conferido: "Encargo Conferido",
  manifestacion_protesta: "Manifestación bajo Protesta",
};

const EXTRACTION_STATUS_BADGE: Record<string, { label: string; className: string }> = {
  pending: { label: "Pendiente", className: "bg-muted text-muted-foreground" },
  processing: { label: "Procesando", className: "bg-warning text-background" },
  extracted: { label: "Extraído", className: "bg-primary/20 text-primary" },
  human_reviewed: { label: "Revisado ✓", className: "bg-success text-background" },
  not_applicable: { label: "Manual", className: "bg-muted text-muted-foreground" },
  error: { label: "Error", className: "bg-destructive text-background" },
};

export default async function ExpedienteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let expediente = null;
  let documentos: Awaited<ReturnType<typeof api.listDocumentos>> = [];
  let consultasSat: unknown[] = [];

  try {
    [expediente, documentos, consultasSat] = await Promise.all([
      api.getExpediente(id),
      api.listDocumentos(id).catch(() => []),
      api.listConsultasSat(id).catch(() => []),
    ]);
  } catch {
    // Not reachable at build time
  }

  if (!expediente) {
    return (
      <main className="max-w-5xl mx-auto px-6 py-8">
        <p className="text-muted-foreground">Expediente no encontrado.</p>
        <Link href="/" className="text-primary hover:underline">← Volver</Link>
      </main>
    );
  }

  const existingDocTypes = documentos.map((d) => d.doc_type);
  const totalRequired = Object.keys(DOC_TYPE_LABELS).length;
  const reviewedCount = documentos.filter((d) => d.extraction_status === "human_reviewed").length;

  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      <StepperHeader currentStep={2} />

      {/* Header */}
      <div className="mb-6">
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          ← Expedientes
        </Link>
        <div className="flex items-start justify-between gap-4 mt-2">
          <div>
            <h1 className="text-2xl font-bold">{expediente.razon_social}</h1>
            <p className="text-muted-foreground font-mono text-sm">{expediente.rfc}</p>
          </div>
          <Link
            href={`/expedientes/${id}/reporte`}
            className="shrink-0 inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all"
          >
            Ver reporte KYB →
          </Link>
        </div>
      </div>

      {/* Progress summary */}
      <div className="rounded-xl border border-border bg-card p-4 mb-6 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Documentos:{" "}
            <strong className="text-foreground">{documentos.length}/{totalRequired}</strong> cargados
            {reviewedCount > 0 && (
              <span className="ml-3 text-success">· {reviewedCount} revisados ✓</span>
            )}
          </span>
          {documentos.length === totalRequired && reviewedCount === totalRequired && (
            <span className="text-success font-medium text-xs">
              ✓ Expediente completo — listo para evaluar
            </span>
          )}
        </div>
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${Math.round((documentos.length / totalRequired) * 100)}%` }}
          />
        </div>
      </div>

      {/* Smart drop zone */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Cargar documentos
        </h2>
        <SmartDropZone
          expedienteId={id}
          existingDocTypes={existingDocTypes}
          onAllDone={() => {}}
        />
      </section>

      {/* Document status grid — only shown once at least 1 doc is uploaded */}
      {documentos.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Estado de documentos
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(DOC_TYPE_LABELS).map(([docType, label]) => {
              const doc = documentos.find((d) => d.doc_type === docType);
              const statusInfo = doc
                ? EXTRACTION_STATUS_BADGE[doc.extraction_status] ?? EXTRACTION_STATUS_BADGE.pending
                : null;
              const canReview =
                doc &&
                (doc.extraction_status === "extracted" ||
                  doc.extraction_status === "not_applicable");

              return (
                <div key={docType} className="rounded-xl border border-border bg-card p-4 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium leading-tight">{label}</p>
                    {statusInfo ? (
                      <Badge className={`shrink-0 text-xs ${statusInfo.className}`}>
                        {statusInfo.label}
                      </Badge>
                    ) : (
                      <Badge className="shrink-0 text-xs bg-muted text-muted-foreground">
                        Sin cargar
                      </Badge>
                    )}
                  </div>
                  {canReview ? (
                    <Link
                      href={`/expedientes/${id}/revisar?documento_id=${doc.id}`}
                      className="inline-flex items-center text-xs text-primary hover:underline"
                    >
                      Revisar campos extraídos →
                    </Link>
                  ) : doc?.extraction_status === "human_reviewed" ? (
                    <p className="text-xs text-success">Revisión completada ✓</p>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Tabs */}
      <Tabs defaultValue="audit">
        <TabsList>
          <TabsTrigger value="documentos">Documentos ({documentos.length})</TabsTrigger>
          <TabsTrigger value="audit">Audit log SAT ({consultasSat.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="documentos" className="mt-4">
          {documentos.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">Sin documentos cargados.</p>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-card">
                  <tr>
                    <th className="text-left px-4 py-3 text-muted-foreground font-medium">Tipo</th>
                    <th className="text-left px-4 py-3 text-muted-foreground font-medium">Método</th>
                    <th className="text-left px-4 py-3 text-muted-foreground font-medium">Estado</th>
                    <th className="text-right px-4 py-3 text-muted-foreground font-medium">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {documentos.map((doc) => {
                    const statusInfo = EXTRACTION_STATUS_BADGE[doc.extraction_status] ?? EXTRACTION_STATUS_BADGE.pending;
                    return (
                      <tr key={doc.id} className="border-t border-border">
                        <td className="px-4 py-3 text-xs">{DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}</td>
                        <td className="px-4 py-3 capitalize text-muted-foreground text-xs">{doc.entry_method}</td>
                        <td className="px-4 py-3">
                          <Badge className={`text-xs ${statusInfo.className}`}>{statusInfo.label}</Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {(doc.extraction_status === "extracted" || doc.extraction_status === "not_applicable") && (
                            <Link href={`/expedientes/${id}/revisar?documento_id=${doc.id}`} className="text-xs text-primary hover:underline">
                              Revisar →
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        <TabsContent value="audit" className="mt-4">
          <p className="text-xs text-muted-foreground mb-3">
            Consultas realizadas contra listas fiscales del SAT (Art. 69, 69-B, 69-B Bis)
          </p>
          {consultasSat.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Sin consultas registradas. Ejecutá una evaluación primero.
            </p>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-card">
                  <tr>
                    <th className="text-left px-3 py-2 text-muted-foreground">Fuente</th>
                    <th className="text-left px-3 py-2 text-muted-foreground">RFC consultado</th>
                    <th className="text-left px-3 py-2 text-muted-foreground">Resultado</th>
                    <th className="text-right px-3 py-2 text-muted-foreground">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {(
                    consultasSat as Array<{
                      id: string;
                      list_type?: string;
                      rfc?: string;
                      resultado?: string;
                      created_at?: string;
                    }>
                  ).map((c) => (
                    <tr key={c.id} className="border-t border-border">
                      <td className="px-3 py-2 font-mono">{c.list_type ?? "—"}</td>
                      <td className="px-3 py-2 font-mono">{c.rfc ?? "—"}</td>
                      <td className="px-3 py-2">{c.resultado ?? "—"}</td>
                      <td className="px-3 py-2 text-right">
                        {c.created_at ? new Date(c.created_at).toLocaleString("es-MX") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </main>
  );
}
```

- [ ] **Step 8.2: Verify locally**

```
cd frontend && pnpm dev
```
Navigate to `http://localhost:3000/expedientes/{any-id}`. Verify:
- Stepper shows Step 2 active
- Drop zone appears with drag-and-drop area
- Progress bar shows document count
- Existing document cards appear below the drop zone

- [ ] **Step 8.3: Commit**

```bash
git add frontend/app/expedientes/[id]/page.tsx
git commit -m "feat: replace document grid with SmartDropZone and progress bar"
```

---

## Task 9: Frontend — Update reporte page

**Files:**
- Modify: `frontend/app/expedientes/[id]/reporte/page.tsx`

**Interfaces:**
- Consumes: `ScoreGauge` (Task 4), `FactorDetailCard` (Task 5), `StepperHeader` (Task 4)
- Consumes: `EvaluationResult.factores_detail` (populated by Task 1 backend change)

- [ ] **Step 9.1: Replace `frontend/app/expedientes/[id]/reporte/page.tsx`**

```tsx
import Link from "next/link";
import { api } from "@/lib/api-client";
import { ScoreGauge } from "@/components/ScoreGauge";
import { FactorDetailCard } from "@/components/FactorDetailCard";
import { StepperHeader } from "@/components/StepperHeader";
import { EvaluateButton } from "./EvaluateButton";

const ACCION_CATEGORY_ICON: Record<string, string> = {
  sat: "🚫",
  discrepancia: "⚠️",
  completitud: "📄",
  otro: "›",
};

export default async function ReportePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let expediente = null;
  let evaluation = null;
  try {
    [expediente, evaluation] = await Promise.all([
      api.getExpediente(id),
      api.getLatestEvaluation(id).catch(() => null),
    ]);
  } catch {
    // Build time
  }

  if (!expediente) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8 flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <p className="text-muted-foreground">Expediente no encontrado.</p>
          <Link href="/" className="text-primary hover:underline mt-4 block">← Volver</Link>
        </div>
      </main>
    );
  }

  const factoresDetail = evaluation?.factores_detail ?? [];
  const factoresConRiesgo = factoresDetail
    .filter((f) => f.points > 0)
    .sort((a, b) => b.points - a.points);
  const factoresSinRiesgo = factoresDetail.filter((f) => f.points === 0);
  const maxPoints = factoresConRiesgo.length
    ? Math.max(...factoresConRiesgo.map((f) => f.points))
    : 100;

  return (
    <main className="max-w-3xl mx-auto px-6 py-8">
      <StepperHeader currentStep={4} />

      {/* Breadcrumb */}
      <div className="mb-6">
        <Link href={`/expedientes/${id}`} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          ← {expediente.razon_social}
        </Link>
        <h1 className="text-2xl font-bold mt-2">Reporte KYB</h1>
        <p className="text-muted-foreground text-sm mt-1 font-mono">{expediente.rfc}</p>
      </div>

      {/* Score hero */}
      <div className="rounded-xl border border-border bg-card p-6 mb-6">
        {evaluation ? (
          <ScoreGauge score={evaluation.score_total} decision={evaluation.decision} />
        ) : (
          <div className="text-center py-4 space-y-3">
            <p className="text-muted-foreground text-sm">
              Aún no hay evaluación. Cargá los documentos y ejecutá la evaluación KYB.
            </p>
            <EvaluateButton expedienteId={id} />
          </div>
        )}
      </div>

      {/* Risk factors */}
      {factoresConRiesgo.length > 0 && (
        <section className="mb-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Factores de riesgo detectados ({factoresConRiesgo.length})
          </h2>
          <div className="space-y-3">
            {factoresConRiesgo.map((f) => (
              <FactorDetailCard key={f.factor_code} factor={f} maxPoints={maxPoints} />
            ))}
          </div>
        </section>
      )}

      {/* Acciones sugeridas */}
      {evaluation?.acciones_sugeridas && evaluation.acciones_sugeridas.length > 0 && (
        <section className="mb-6">
          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
              Acciones requeridas ({evaluation.acciones_sugeridas.length})
            </h2>
            <ul className="space-y-4">
              {evaluation.acciones_sugeridas.map((accion, i) => {
                const relatedFactor = factoresConRiesgo.find((f) =>
                  accion.toLowerCase().includes(f.factor_code.split("_")[0])
                );
                const icon = relatedFactor
                  ? ACCION_CATEGORY_ICON[relatedFactor.category]
                  : "›";
                return (
                  <li key={i} className="flex items-start gap-3">
                    <span className="shrink-0 mt-0.5 text-base">{icon}</span>
                    <div className="space-y-1">
                      <p className="text-sm">{accion}</p>
                      {relatedFactor?.legal_ref && (
                        <p className="text-xs text-muted-foreground">
                          § {relatedFactor.legal_ref.split("—")[0].trim()}
                        </p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>
      )}

      {/* Factors with 0 points (collapsed) */}
      {factoresSinRiesgo.length > 0 && (
        <section className="mb-6">
          <details>
            <summary className="text-xs text-muted-foreground uppercase tracking-wide cursor-pointer hover:text-foreground transition-colors mb-2 select-none">
              Factores verificados sin impacto en score ({factoresSinRiesgo.length})
            </summary>
            <div className="mt-3 space-y-3">
              {factoresSinRiesgo.map((f) => (
                <FactorDetailCard key={f.factor_code} factor={f} maxPoints={maxPoints} />
              ))}
            </div>
          </details>
        </section>
      )}

      {/* Expediente metadata */}
      <div className="rounded-xl border border-border bg-card p-6 mb-6">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Datos del expediente
        </h2>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-muted-foreground text-xs">RFC</dt>
            <dd className="font-mono">{expediente.rfc}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Estado</dt>
            <dd className="capitalize">{expediente.status}</dd>
          </div>
          {expediente.domicilio_fiscal && (
            <div className="col-span-2">
              <dt className="text-muted-foreground text-xs">Domicilio fiscal</dt>
              <dd>{expediente.domicilio_fiscal}</dd>
            </div>
          )}
          {expediente.representante_legal && (
            <div className="col-span-2">
              <dt className="text-muted-foreground text-xs">Representante legal</dt>
              <dd>{expediente.representante_legal}</dd>
            </div>
          )}
          {evaluation?.evaluated_at && (
            <div className="col-span-2">
              <dt className="text-muted-foreground text-xs">Última evaluación</dt>
              <dd>{new Date(evaluation.evaluated_at).toLocaleString("es-MX")}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Actions */}
      <div className="flex gap-3 flex-wrap">
        <EvaluateButton expedienteId={id} />
        <Link
          href={`/expedientes/${id}`}
          className="inline-flex items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted transition-all"
        >
          Ver documentos
        </Link>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted transition-all"
        >
          ← Dashboard
        </Link>
      </div>
    </main>
  );
}
```

- [ ] **Step 9.2: Run full build**

```
cd frontend && pnpm build
```
Expected: build succeeds with zero TypeScript errors

- [ ] **Step 9.3: Verify locally**

```
cd frontend && pnpm dev
```
Navigate to `http://localhost:3000/expedientes/{id-with-evaluation}/reporte`. Verify:
- Stepper shows Step 4 active
- ScoreGauge renders colored horizontal bar
- Each risk factor shows as a card with `§ Regla 1.4.14 RGCE 2026...` legal ref in the gray box
- "Factores verificados sin impacto" section is collapsed by default
- Acciones sugeridas each have a legal ref line below

- [ ] **Step 9.4: Commit**

```bash
git add frontend/app/expedientes/[id]/reporte/page.tsx
git commit -m "feat: enhance reporte with ScoreGauge, FactorDetailCard, legal citations, stepper"
```

---

## Self-Review

**Spec coverage:**
- [x] Step 1 (datos empresa): Task 7 — redirect fix + stepper + RFC inline validation
- [x] Step 2 (cargar docs): Tasks 2 + 6 + 8 — classify endpoint + SmartDropZone + page
- [x] Step 3 (pipeline): Task 6 — inline per-file status (classifying → uploading → extracting → done)
- [x] Step 4 (reporte): Tasks 1 + 4 + 5 + 9 — factores_detail + ScoreGauge + FactorDetailCard + page
- [x] Backend classify endpoint: Task 2
- [x] Backend factores_detail in evaluation API: Task 1
- [x] Legal references map: Task 1 (legal_refs.py)
- [x] `extraer_texto_de_bytes`: Task 2, step 2.3
- [x] `get_latest_evaluation` bug fixed: Task 1, step 1.6

**Type consistency:**
- `FactorDetail` — defined Task 3, consumed Tasks 5 and 9 ✓
- `ClassifyResult` — defined Task 3, consumed Task 6 ✓
- `api.classifyDocumento(file: File)` — defined Task 3, called Task 6 ✓
- `EvaluationResult.factores_detail: FactorDetail[]` — defined Task 3, populated Task 1 backend, consumed Task 9 ✓
- `SmartDropZone` props (`expedienteId`, `existingDocTypes`, `onAllDone`) — defined Task 6, consumed Task 8 ✓
- `StepperHeader` prop (`currentStep: 1|2|3|4`) — defined Task 4, consumed Tasks 7, 8, 9 ✓
- `ScoreGauge` props (`score: number`, `decision: string`) — defined Task 4, consumed Task 9 ✓
- `LEGAL_REFS` — defined Task 1 backend, imported by evaluation_service in Task 1 ✓

**Bug notes:**
- Task 7 step 7.1 contains a typo (`{rfcErr}` → `{rfcError}`) — documented inline with correction
- `get_latest_evaluation` currently has a bug (maps `critical_blocks` to hardcoded 100 pts) — fixed in Task 1 step 1.6
