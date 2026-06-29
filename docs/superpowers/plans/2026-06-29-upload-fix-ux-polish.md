# Upload Fix & UX Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 confirmed backend 500 errors (broken upload flow, extract reads local filesystem, wrong column name) and polish the frontend UX so document upload, report detail, and review flows work end-to-end.

**Architecture:** Replace the broken 3-step upload flow (crearDocumento → PUT signed_url → extractDocumento) with a single `POST /documentos/upload` multipart endpoint that uploads to Supabase Storage server-side using service_role (bypasses RLS) and extracts text inline. Frontend SmartDropZone calls this one endpoint. Report and review pages get enriched per-factor-code guidance with verifiable legal references.

**Tech Stack:** FastAPI + Python 3.13 (uv), supabase-py / storage3, Next.js App Router + TypeScript, Tailwind + shadcn/ui. Tests: pytest with mocked Supabase client.

## Global Constraints

- Python 3.13 pinned (`backend/.python-version`). Never touch `pyproject.toml` by hand — use `uv add`.
- `uv run pytest src/tests/ -v` is the backend test command (run from `backend/`).
- `pnpm dev` / `pnpm build` for the frontend (run from `frontend/`).
- Never pip/poetry/npm/yarn. Never commit `.env` files.
- Follow existing patterns: pytest with mocked `supabase` fixture, Next.js App Router server components.
- Vercel auto-deploys on push to `main`. Backend: `backend-nine-snowy-67.vercel.app`. Frontend: `frontend-khaki-eight-25.vercel.app`.
- `consultas_sat` timestamp column is `consulted_at`, NOT `created_at`.
- No raw JSON visible to end users anywhere.
- All UI labels in Spanish; code identifiers in English.

---

### Task 1: Fix `consultas_sat` query — `consulted_at` not `created_at`

**Files:**
- Modify: `backend/src/api/routers/expedientes.py:74`

**Interfaces:**
- Consumes: nothing new
- Produces: `GET /expedientes/{id}/consultas-sat` returns 200 instead of 500

- [ ] **Step 1: Write the failing test**

Add to `backend/src/tests/test_expedientes_router.py` (find the existing test file and add):

```python
def test_get_consultas_sat_uses_consulted_at(supabase):
    """Verify the query orders by consulted_at (not created_at which does not exist)."""
    supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    resp = client.get("/expedientes/some-id/consultas-sat")
    assert resp.status_code == 200
    # Verify the column used in order()
    order_call = supabase.table.return_value.select.return_value.eq.return_value.order
    order_call.assert_called_once_with("consulted_at", desc=True)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest src/tests/test_expedientes_router.py -k "test_get_consultas_sat" -v
```

Expected: FAIL — order called with `"created_at"`, not `"consulted_at"`.

- [ ] **Step 3: Apply the 1-line fix**

In `backend/src/api/routers/expedientes.py`, line 74:

```python
@router.get("/{expediente_id}/consultas-sat")
def get_consultas_sat(expediente_id: str, supabase: Client = Depends(get_supabase_client)):
    result = (
        supabase.table("consultas_sat")
        .select("*")
        .eq("expediente_id", expediente_id)
        .order("consulted_at", desc=True)   # was: "created_at"
        .execute()
    )
    return result.data
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest src/tests/test_expedientes_router.py -k "test_get_consultas_sat" -v
```

Expected: PASS.

- [ ] **Step 5: Run full backend test suite**

```bash
cd backend && uv run pytest src/tests/ -v
```

Expected: all green, no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/routers/expedientes.py
git commit -m "fix: use consulted_at column in consultas_sat query"
```

---

### Task 2: Add `POST /documentos/upload` — unified upload + extract endpoint

This replaces the broken 3-step flow (create → signed URL → extract). The service_role client uploads directly to Supabase Storage, bypassing the RLS issue entirely.

**Files:**
- Modify: `backend/src/api/routers/documentos.py`
- Create: `backend/src/tests/test_upload_endpoint.py`

**Interfaces:**
- Consumes: `extraer_texto_de_bytes(content: bytes) -> str` from `infrastructure.ai.pdf`, `extraer_campos(supabase, doc_type, texto) -> dict` from `infrastructure.ai.extract`, `SCHEMA_REGISTRY` from `infrastructure.ai.schemas`
- Produces: `POST /documentos/upload` → `{documento_id, doc_type, fields, extraction_status}` or 409 `{detail: {documento_id, message}}`

- [ ] **Step 1: Write the failing tests**

Create `backend/src/tests/test_upload_endpoint.py`:

```python
import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(supabase):
    from main import app
    return TestClient(app)


def _make_pdf_bytes() -> bytes:
    """Minimal valid-looking PDF bytes for testing (not actually parsed)."""
    return b"%PDF-1.4 test content"


def test_upload_creates_documento(client, supabase):
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "doc-123"}]
    supabase.storage.from_.return_value.upload.return_value = {"path": "exp-1/csf.pdf"}

    with patch("api.routers.documentos.extraer_texto_de_bytes", return_value="RFC: EKU9003173C9"):
        with patch("api.routers.documentos.extraer_campos", return_value={"rfc": "EKU9003173C9"}):
            resp = client.post(
                "/documentos/upload",
                data={"expediente_id": "exp-1", "doc_type": "csf"},
                files={"file": ("csf.pdf", _make_pdf_bytes(), "application/pdf")},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert "documento_id" in body
    assert body["doc_type"] == "csf"
    assert body["extraction_status"] == "extracted"


def test_upload_returns_409_on_duplicate(client, supabase):
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": "existing-doc-id"}
    ]

    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": "exp-1", "doc_type": "csf"},
        files={"file": ("csf.pdf", _make_pdf_bytes(), "application/pdf")},
    )

    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["documento_id"] == "existing-doc-id"


def test_upload_rejects_invalid_doc_type(client, supabase):
    resp = client.post(
        "/documentos/upload",
        data={"expediente_id": "exp-1", "doc_type": "invalid_type"},
        files={"file": ("x.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest src/tests/test_upload_endpoint.py -v
```

Expected: FAIL — endpoint does not exist yet.

- [ ] **Step 3: Implement the endpoint**

Add to `backend/src/api/routers/documentos.py` (after the existing imports, before the router definition line is fine, but add the new endpoint BEFORE the `/classify` route — FastAPI matches routes top-to-bottom and `/upload` must not be shadowed by `/{documento_id}`):

New imports to add at the top of `documentos.py`:

```python
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
```

(Replace the existing `from fastapi import APIRouter, Depends, File, HTTPException, UploadFile` line — just add `Form`.)

New endpoint — add it right after the `crear_documento` function (before `extract_documento`):

```python
@router.post("/upload")
async def upload_documento(
    expediente_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    supabase=Depends(get_supabase_client),
):
    if doc_type not in SCHEMA_REGISTRY:
        raise HTTPException(
            status_code=422,
            detail=f"doc_type inválido: {doc_type!r}. Valores: {sorted(SCHEMA_REGISTRY)}",
        )

    # Guard: reject duplicate doc_type for this expediente
    existing = (
        supabase.table("documentos")
        .select("id")
        .eq("expediente_id", expediente_id)
        .eq("doc_type", doc_type)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=409,
            detail={"documento_id": existing.data[0]["id"], "message": "Ya existe un documento de este tipo en el expediente"},
        )

    content = await file.read()
    storage_path = f"{expediente_id}/{doc_type}.pdf"

    # Upload directly via service_role — bypasses storage RLS
    supabase.storage.from_("kyb-docs").upload(
        path=storage_path,
        file=content,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )

    # Extract text and fields inline (no local filesystem read)
    texto = extraer_texto_de_bytes(content)
    campos = extraer_campos(supabase, doc_type, texto) if texto.strip() else {}

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
            "extraction_status": "extracted" if campos else "pending",
        }
    ).execute()

    return {
        "documento_id": documento_id,
        "doc_type": doc_type,
        "fields": campos,
        "extraction_status": "extracted" if campos else "pending",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest src/tests/test_upload_endpoint.py -v
```

Expected: all 3 PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd backend && uv run pytest src/tests/ -v
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/routers/documentos.py backend/src/tests/test_upload_endpoint.py
git commit -m "feat: add POST /documentos/upload — unified server-side upload+extract"
```

---

### Task 3: Update `api-client.ts` — add `uploadDocumento`, type for 409

**Files:**
- Modify: `frontend/lib/api-client.ts`

**Interfaces:**
- Consumes: new `POST /documentos/upload` endpoint from Task 2
- Produces: `api.uploadDocumento(expedienteId, docType, file)` → `{documento_id, doc_type, fields, extraction_status}` or throws `DuplicateDocumentoError`

- [ ] **Step 1: Add the export and method**

In `frontend/lib/api-client.ts`, add after the existing type definitions (after `SatImportRun`) and the new method inside `export const api = { ... }`:

```typescript
export class DuplicateDocumentoError extends Error {
  constructor(public readonly documentoId: string) {
    super("Documento de este tipo ya existe en el expediente");
    this.name = "DuplicateDocumentoError";
  }
}

export type UploadDocumentoResult = {
  documento_id: string;
  doc_type: string;
  fields: Record<string, unknown>;
  extraction_status: string;
};
```

Inside `export const api = { ... }`, add after `classifyDocumento`:

```typescript
  uploadDocumento: async (
    expedienteId: string,
    docType: string,
    file: File
  ): Promise<UploadDocumentoResult> => {
    const form = new FormData();
    form.append("expediente_id", expedienteId);
    form.append("doc_type", docType);
    form.append("file", file);
    const res = await fetch(`${API_URL}/documentos/upload`, {
      method: "POST",
      body: form,
    });
    if (res.status === 409) {
      const data = await res.json();
      throw new DuplicateDocumentoError(data.detail?.documento_id ?? "");
    }
    if (!res.ok) throw new Error(`Upload error ${res.status}: ${await res.text()}`);
    return res.json();
  },
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm build 2>&1 | head -40
```

Expected: no TypeScript errors on `api-client.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api-client.ts
git commit -m "feat: add uploadDocumento to api-client — single-call upload+extract"
```

---

### Task 4: Fix `SmartDropZone` — use 1-call `uploadDocumento` + page refresh

Replaces the broken 3-step `crearDocumento → fetch(signed_url) → extractDocumento` with a single `api.uploadDocumento` call. Adds `router.refresh()` after all files finish so the server component re-fetches the document list.

**Files:**
- Modify: `frontend/components/SmartDropZone.tsx`

**Interfaces:**
- Consumes: `api.uploadDocumento`, `DuplicateDocumentoError` from Task 3
- Produces: working SmartDropZone that fills the expediente document grid after upload

- [ ] **Step 1: Update `processAll` in `SmartDropZone.tsx`**

Replace the entire `processAll` function (lines ~154–181) and the `useEffect` (lines ~193–197) with:

```typescript
  async function processAll() {
    const toProcess = files.filter((f) => f.status === "classified" && f.docType !== "unknown");
    if (!toProcess.length) return;
    setProcessing(true);

    await Promise.all(
      toProcess.map(async ({ key, file, docType }) => {
        const update = (status: FileState["status"], extra?: Partial<FileState>) =>
          setFiles((prev) =>
            prev.map((f) => f.key === key ? { ...f, status, ...extra } : f)
          );
        try {
          update("uploading");
          const result = await api.uploadDocumento(expedienteId, docType, file);
          update("done", { documentoId: result.documento_id });
        } catch (err) {
          if (err instanceof DuplicateDocumentoError) {
            update("done", { documentoId: err.documentoId, errorMsg: "Ya existía — usando el registro anterior" });
          } else {
            update("error", { errorMsg: err instanceof Error ? err.message : "Error al procesar" });
          }
        }
      })
    );

    setProcessing(false);
    router.refresh();   // re-fetches server component data → updates document grid
  }
```

Also update the import at the top of the file to include `DuplicateDocumentoError`:

```typescript
import { api, DuplicateDocumentoError } from "@/lib/api-client";
```

Update the `FileState` status type — remove `"extracting"` since it no longer exists as a separate step:

```typescript
type FileState = {
  key: string;
  file: File;
  status: "classifying" | "classified" | "uploading" | "done" | "error";
  docType: string;
  confidence: "high" | "low";
  suggestedLabel: string;
  errorMsg?: string;
  documentoId?: string;
};
```

Update `StatusIcon` — remove the `"extracting"` case (fold into `"uploading"`):

```typescript
  function StatusIcon({ f }: { f: FileState }) {
    if (f.status === "done") return <CheckCircle2 className="size-4 text-success shrink-0" />;
    if (f.status === "error") return <XCircle className="size-4 text-destructive shrink-0" />;
    if (f.status === "classifying" || f.status === "uploading")
      return <Loader2 className="size-4 text-muted-foreground shrink-0 animate-spin" />;
    if (f.confidence === "high") return <CheckCircle2 className="size-4 text-primary shrink-0" />;
    return <AlertTriangle className="size-4 text-warning shrink-0" />;
  }
```

Update the status label text in the JSX (find the `<span>` that shows status text, remove `extracting` case):

```tsx
                  {f.status === "error" ? (f.errorMsg ?? "Error")
                    : f.status === "classifying" ? "Clasificando con IA..."
                    : f.status === "uploading" ? "Subiendo y extrayendo con IA..."
                    : f.status === "done" ? (f.errorMsg ?? "Procesado")
                    : ""}
```

- [ ] **Step 2: Verify the app compiles**

```bash
cd frontend && pnpm build 2>&1 | head -60
```

Expected: no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/SmartDropZone.tsx
git commit -m "fix: SmartDropZone — single-call upload, remove broken signed URL flow, add router.refresh"
```

---

### Task 5: Fix `DocumentUploader` — use `uploadDocumento`

`DocumentUploader` has the same broken 3-step flow as SmartDropZone.

**Files:**
- Modify: `frontend/components/DocumentUploader.tsx`

**Interfaces:**
- Consumes: `api.uploadDocumento`, `DuplicateDocumentoError` from Task 3
- Produces: working `DocumentUploader` component

- [ ] **Step 1: Replace `subirArchivo` in `DocumentUploader.tsx`**

Replace the entire `subirArchivo` function (lines ~26–52):

```typescript
  async function subirArchivo(file: File) {
    setEstado("uploading");
    setErrorMsg(null);
    setPasoActual(0);
    try {
      const result = await api.uploadDocumento(expedienteId, docType, file);
      setDocId(result.documento_id);
      setPasoActual(3);
      setEstado("done");
      onDone?.();
      router.refresh();
    } catch (err) {
      if (err instanceof DuplicateDocumentoError && err.documentoId) {
        // Treat duplicate as success — navigate to existing doc
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

Update the import at the top:

```typescript
import { api, DuplicateDocumentoError } from "@/lib/api-client";
```

The `PIPELINE_PASOS` constant and progress display can stay as-is (they just won't show interim steps since upload+extract is now a single call — `pasoActual` will jump from 0 to 3 directly, which is fine visually).

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm build 2>&1 | head -60
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/DocumentUploader.tsx
git commit -m "fix: DocumentUploader — use uploadDocumento, remove broken 3-step flow"
```

---

### Task 6: Enrich `ActionCard` with per-factor-code detailed guidance + SAT links

Currently `ActionCard` shows a single generic sentence. This task replaces that with structured, specific guidance per factor code including verifiable SAT links.

**Files:**
- Modify: `frontend/components/ActionCard.tsx`

**Interfaces:**
- Consumes: `FactorDetail` from `api-client.ts` (same type, no changes)
- Produces: `ActionCard` with specific multi-step guidance and external references

- [ ] **Step 1: Replace `ActionCard.tsx` with enriched version**

Full replacement of `frontend/components/ActionCard.tsx`:

```tsx
import { ShieldAlert, AlertTriangle, FolderSearch, FileCheck2, Scale, ExternalLink, Clock } from "lucide-react";
import type React from "react";
import type { FactorDetail } from "@/lib/api-client";

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  sat: <ShieldAlert className="size-4 text-destructive shrink-0 mt-0.5" />,
  discrepancia: <AlertTriangle className="size-4 text-warning shrink-0 mt-0.5" />,
  completitud: <FolderSearch className="size-4 text-primary shrink-0 mt-0.5" />,
  otro: <FileCheck2 className="size-4 text-muted-foreground shrink-0 mt-0.5" />,
};

const PRIORITY_LABEL: Record<string, { label: string; className: string }> = {
  sat: { label: "Bloqueo / alta prioridad", className: "bg-destructive/15 text-destructive" },
  discrepancia: { label: "Prioridad media", className: "bg-warning/15 text-warning" },
  completitud: { label: "Prioridad estándar", className: "bg-primary/15 text-primary" },
  otro: { label: "Informativo", className: "bg-muted text-muted-foreground" },
};

type DetailedAction = {
  summary: string;
  steps: string[];
  verifyUrl?: string;
  verifyLabel?: string;
  urgency?: string;
};

const FACTOR_ACTIONS: Record<string, DetailedAction> = {
  sat_69b_definitivo: {
    summary: "No operar bajo ninguna circunstancia hasta obtener resolución formal del SAT.",
    steps: [
      "Verificar la presencia en el listado definitivo en sat.gob.mx (Trámites → Consultas → Listado 69-B).",
      "Notificar formalmente al cliente por escrito y documentar la comunicación en el expediente.",
      "Consultar al área jurídica de la agencia antes de cualquier acción adicional.",
      "No emitir ni aceptar CFDIs vinculados a este RFC.",
      "Si el cliente impugna, solicitar la resolución de desvirtuación emitida por el SAT antes de reabrir el expediente.",
    ],
    verifyUrl: "https://www.sat.gob.mx/consultas/listado_69b",
    verifyLabel: "Verificar en sat.gob.mx → Listado 69-B",
    urgency: "Inmediato — no postergar",
  },
  sat_69b_presunto: {
    summary: "RFC en proceso de revisión SAT por presunta emisión de CFDI sin respaldo.",
    steps: [
      "Verificar el estado actual en sat.gob.mx (Trámites → Consultas → Listado 69-B Presuntos).",
      "Iniciar diligencia ampliada: solicitar al cliente carta de no vinculación con CFDIs observados.",
      "Esperar la resolución del SAT antes de proceder a la inscripción en el padrón.",
      "Documentar cada paso del proceso en el expediente físico.",
    ],
    verifyUrl: "https://www.sat.gob.mx/consultas/listado_69b",
    verifyLabel: "Verificar en sat.gob.mx → Listado 69-B",
    urgency: "Antes de continuar el onboarding",
  },
  sat_69b_bis: {
    summary: "RFC en el listado de transmisión indebida de pérdidas fiscales.",
    steps: [
      "Verificar la presencia en el listado 69-B Bis en sat.gob.mx.",
      "Solicitar al cliente aclaración escrita ante el SAT sobre las pérdidas fiscales cuestionadas.",
      "Obtener resolución del SAT que aclare la situación antes de inscribir al padrón.",
    ],
    verifyUrl: "https://www.sat.gob.mx/consultas/listado_69b_bis",
    verifyLabel: "Verificar en sat.gob.mx → Listado 69-B Bis",
    urgency: "Antes de inscripción al padrón",
  },
  sat_69_incumplido: {
    summary: "Contribuyente con obligaciones fiscales incumplidas según el SAT.",
    steps: [
      "Verificar la categoría de incumplimiento (firmes, exigibles, CSD sin efectos, no localizado) en sat.gob.mx.",
      "Requerir al cliente aclaración de situación fiscal y documentación que acredite la resolución del adeudo.",
      "No inscribir al padrón hasta obtener constancia de situación fiscal limpia.",
    ],
    verifyUrl: "https://www.sat.gob.mx/consultas/listado_69",
    verifyLabel: "Verificar en sat.gob.mx → Art. 69 CFF",
    urgency: "Antes de inscripción al padrón",
  },
  disc_rfc: {
    summary: "El RFC no coincide entre los documentos del expediente.",
    steps: [
      "Identificar cuál documento tiene el RFC diferente (revisar CSF, acta constitutiva, poder notarial).",
      "Solicitar al cliente la versión corregida del documento con error.",
      "Reemplazar el documento corregido en el expediente y volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la evaluación final",
  },
  disc_razon_social: {
    summary: "La razón social no coincide entre los documentos del expediente.",
    steps: [
      "Identificar qué documento tiene la variación (abreviatura societaria vs nombre completo, typo, etc.).",
      "Si la diferencia es solo abreviatura societaria (SA de CV vs S.A. de C.V.), documentar la aclaración.",
      "Si es un nombre diferente, solicitar al cliente el documento corregido.",
      "Recargar el documento corregido y volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la evaluación final",
  },
  disc_domicilio: {
    summary: "El domicilio fiscal no coincide entre los documentos.",
    steps: [
      "Comparar el domicilio en la CSF, el comprobante de domicilio y el formulario del expediente.",
      "Si hay cambio de domicilio reciente, solicitar CSF actualizada al cliente.",
      "Actualizar los campos del expediente con el domicilio vigente y volver a evaluar.",
    ],
    urgency: "Antes de la evaluación final",
  },
  disc_representante: {
    summary: "El nombre del representante legal no coincide entre poder, identificación y formulario.",
    steps: [
      "Comparar el nombre exactamente entre el poder notarial, la identificación oficial y el encargo conferido.",
      "Solicitar al cliente aclaración escrita si difieren (nombre compuesto vs abreviado).",
      "Si hay error en algún documento, solicitar la versión corregida.",
    ],
    urgency: "Antes de la evaluación final",
  },
  disc_fechas: {
    summary: "Inconsistencias de fechas entre documentos del expediente.",
    steps: [
      "Revisar las fechas de emisión y vigencia en cada documento.",
      "Verificar que el comprobante de domicilio tenga menos de 90 días.",
      "Verificar que la CSF corresponda al mes calendario vigente.",
      "Solicitar documentos actualizados para los que estén vencidos.",
    ],
    urgency: "Antes de la evaluación final",
  },
  doc_missing: {
    summary: "Hay uno o más documentos requeridos que no han sido cargados.",
    steps: [
      "Identificar qué documento falta en la sección 'Estado de documentos' del expediente.",
      "Solicitar al cliente el documento faltante.",
      "Cargar el PDF desde la zona de arrastre o con el botón de carga.",
      "Volver a ejecutar la evaluación una vez cargado.",
    ],
    urgency: "Antes de la evaluación final",
  },
  doc_expired: {
    summary: "El comprobante de domicilio tiene más de 90 días de antigüedad.",
    steps: [
      "Solicitar al cliente un comprobante de domicilio reciente (máximo 90 días: recibo CFE, TELMEX, agua, estado de cuenta bancario).",
      "Reemplazar el documento en el expediente.",
      "Volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la inscripción al padrón",
  },
  csf_stale: {
    summary: "La CSF no corresponde al mes calendario vigente.",
    steps: [
      "El cliente debe generar una nueva CSF desde el portal del SAT (mi.sat.gob.mx → RFC y CSF → Genera tu CSF).",
      "Reemplazar la CSF en el expediente con la versión del mes actual.",
      "Volver a ejecutar la evaluación.",
    ],
    verifyUrl: "https://www.sat.gob.mx/tramites/45247/genera-tu-constancia-de-situacion-fiscal",
    verifyLabel: "Generar CSF en mi.sat.gob.mx",
    urgency: "Antes de la inscripción al padrón",
  },
  manifestacion_incompleta: {
    summary: "La Manifestación bajo Protesta no incluye la cláusula de los Art. 69-B y 49 Bis CFF.",
    steps: [
      "Revisar el template de la Manifestación bajo Protesta de Decir Verdad.",
      "Verificar que incluya explícitamente la declaración de no encontrarse en los listados del Art. 69-B CFF y Art. 49 Bis CFF.",
      "Solicitar al cliente que firme la versión correcta del documento.",
      "Reemplazar el documento en el expediente y volver a revisar los campos extraídos.",
    ],
    urgency: "Antes de la evaluación final",
  },
  socios_incompletos: {
    summary: "No se registraron socios, accionistas ni beneficiario controlador del acta constitutiva.",
    steps: [
      "Revisar el acta constitutiva para identificar a todos los socios y sus porcentajes de participación.",
      "Registrar a cada socio con nombre completo, RFC y porcentaje desde la pantalla de revisión del documento.",
      "Identificar al beneficiario controlador (persona física con ≥25% del capital o control efectivo).",
      "Volver a ejecutar la evaluación.",
    ],
    urgency: "Requerido por LFPIORPI y Regla 1.4.14 RGCE",
  },
  rep_legal_incompleto: {
    summary: "No se capturó el nombre completo del representante legal.",
    steps: [
      "Revisar la identificación oficial del representante legal y capturar el nombre completo.",
      "Confirmar que coincide con el nombre en el poder notarial.",
      "Guardar la revisión y volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la evaluación final",
  },
  rfc_formato_invalido: {
    summary: "El RFC no cumple con el formato oficial mexicano.",
    steps: [
      "Verificar el RFC en la CSF (fuente primaria oficial).",
      "Corregir el RFC en los datos del expediente.",
      "Volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de cualquier consulta SAT",
  },
};

type Props = {
  accion: string;
  relatedFactor?: FactorDetail;
  index: number;
};

export function ActionCard({ accion, relatedFactor, index }: Props) {
  const category = relatedFactor?.category ?? "otro";
  const icon = CATEGORY_ICON[category];
  const priority = PRIORITY_LABEL[category];
  const detail = relatedFactor ? FACTOR_ACTIONS[relatedFactor.factor_code] : undefined;

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground mt-0.5">
          {index + 1}
        </div>
        {icon}
        <div className="flex-1 space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${priority.className}`}>
              {priority.label}
            </span>
            {detail?.urgency && (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="size-3" />
                {detail.urgency}
              </span>
            )}
          </div>
          <p className="text-sm font-medium leading-snug">{detail?.summary ?? accion}</p>
        </div>
      </div>

      {/* Specific steps */}
      {detail?.steps && detail.steps.length > 0 && (
        <ol className="space-y-1.5 ml-9">
          {detail.steps.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-foreground/80 leading-relaxed">
              <span className="shrink-0 font-semibold text-muted-foreground mt-0.5">{i + 1}.</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      )}

      {/* Legal ref */}
      {relatedFactor?.legal_ref && (
        <div className="flex items-start gap-1.5 ml-9">
          <Scale className="size-3 shrink-0 mt-0.5 text-muted-foreground" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            {relatedFactor.legal_ref}
          </p>
        </div>
      )}

      {/* Verify URL */}
      {detail?.verifyUrl && (
        <div className="ml-9">
          <a
            href={detail.verifyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
          >
            <ExternalLink className="size-3" />
            {detail.verifyLabel ?? "Verificar en fuente oficial"}
          </a>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm build 2>&1 | head -60
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ActionCard.tsx
git commit -m "feat: enrich ActionCard with per-factor-code specific steps and SAT links"
```

---

### Task 7: Expand `legal_ref` by default for critical/high-points `FactorDetailCard`

Currently `legal_ref` is hidden in a `<details>` collapsed by default. For critical factors (is_critical_block or points ≥ 35), show it expanded.

**Files:**
- Modify: `frontend/components/FactorDetailCard.tsx`

**Interfaces:**
- Consumes: `FactorDetail` (unchanged)
- Produces: same `FactorDetailCard` but with legal citation visible for important factors

- [ ] **Step 1: Update the `<details>` in `FactorDetailCard.tsx`**

Find the `<details className="group">` block (around line 153) and replace it with:

```tsx
      {/* Legal citation — expanded by default for high-severity factors */}
      {factor.legal_ref && (
        <details className="group" open={isCritical || factor.points >= 35}>
          <summary className="flex items-center gap-1.5 cursor-pointer text-xs text-muted-foreground hover:text-foreground transition-colors select-none list-none">
            <BookOpen className="size-3.5 shrink-0" />
            <span>Fundamento legal</span>
            <ChevronDown className="size-3 transition-transform group-open:rotate-180 ml-auto" />
          </summary>
          <div className="mt-2 rounded-lg bg-muted/60 px-3 py-2">
            <p className="text-xs text-muted-foreground leading-relaxed">{factor.legal_ref}</p>
          </div>
        </details>
      )}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm build 2>&1 | head -40
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/FactorDetailCard.tsx
git commit -m "feat: expand legal_ref by default for critical and high-risk factors"
```

---

### Task 8: Add "Review next document" flow to `RevisarPage`

After confirming one document's review, the user currently has to navigate back to the expediente and click another document. This adds a "next doc to review" button directly on the confirmation screen.

**Files:**
- Modify: `frontend/app/expedientes/[id]/revisar/page.tsx`

**Interfaces:**
- Consumes: `api.listDocumentos` (already used)
- Produces: confirmation screen that shows how many docs still need review and offers a direct link to the next one

- [ ] **Step 1: Update the `saved` state render in `revisar/page.tsx`**

Find the `if (saved)` block (around line 119) and replace it with:

```tsx
  const [remainingDocs, setRemainingDocs] = useState<{ id: string; doc_type: string }[]>([]);

  // Load remaining docs needing review after save
  useEffect(() => {
    if (!saved) return;
    api.listDocumentos(id).then((docs) => {
      const needReview = docs.filter(
        (d) =>
          d.id !== documento_id &&
          (d.extraction_status === "extracted" || d.extraction_status === "not_applicable")
      );
      setRemainingDocs(needReview.map((d) => ({ id: d.id, doc_type: d.doc_type })));
    }).catch(() => {});
  }, [saved, id, documento_id]);

  if (saved) {
    const nextDoc = remainingDocs[0];
    return (
      <main className="max-w-4xl mx-auto px-6 py-8 flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4 max-w-sm">
          <div className="w-12 h-12 rounded-full bg-success/15 flex items-center justify-center mx-auto">
            <CheckCircle2 className="size-6 text-success" />
          </div>
          <p className="text-lg font-semibold">Revisión guardada</p>
          <p className="text-muted-foreground text-sm">
            Los campos fueron confirmados con revisión humana.
          </p>

          {remainingDocs.length > 0 ? (
            <div className="rounded-xl border border-border bg-card p-4 space-y-3 text-left">
              <p className="text-sm font-medium">
                {remainingDocs.length} documento{remainingDocs.length !== 1 ? "s" : ""} más por revisar
              </p>
              {nextDoc && (
                <Button
                  className="w-full"
                  onClick={() => router.push(`/expedientes/${id}/revisar?documento_id=${nextDoc.id}`)}
                >
                  Revisar siguiente documento →
                </Button>
              )}
              <Button
                variant="outline"
                className="w-full"
                onClick={() => router.push(`/expedientes/${id}`)}
              >
                Ver todos los documentos
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-success font-medium">
                ✓ Todos los documentos revisados
              </p>
              <Button
                className="w-full"
                onClick={() => router.push(`/expedientes/${id}/reporte`)}
              >
                Ver reporte KYB →
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => router.push(`/expedientes/${id}`)}
              >
                Volver al expediente
              </Button>
            </div>
          )}
        </div>
      </main>
    );
  }
```

Also add the missing import at the top of the file:

```typescript
import { CheckCircle2 } from "lucide-react";
```

And add `remainingDocs` state and `useEffect` to the component. Make sure `useState` is already imported (it is).

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm build 2>&1 | head -60
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/expedientes/[id]/revisar/page.tsx
git commit -m "feat: revisar page shows next-document flow after confirming review"
```

---

### Task 9: Deploy and smoke-test

Push to `main`, wait for Vercel to deploy both projects, then manually verify the critical paths.

**Files:** none — deploy only

- [ ] **Step 1: Push all commits to main**

```bash
git push origin feat/ux-improvements
```

Wait for both Vercel deployments to turn green (usually ~2 min each).

- [ ] **Step 2: Smoke test — upload flow**

Open `https://frontend-khaki-eight-25.vercel.app`. Pick an existing expediente (or create one). Drop one of the demo PDFs from `backend/scripts/demo_pdfs/` on the SmartDropZone. Verify:
- Status shows "Subiendo y extrayendo con IA..." then "Procesado" (no 500 error)
- Document appears in the Status Grid below without page reload being needed
- Dropping the same PDF again shows "Ya existía" or is silently skipped

- [ ] **Step 3: Smoke test — consultas-sat audit tab**

On the expediente detail page, click "Audit log SAT" tab. Verify it shows data (or "Sin consultas registradas") instead of a 500 error. Then click "Ejecutar evaluación KYB" and re-check the tab — it should now show the SAT lookup entries.

- [ ] **Step 4: Smoke test — report quality**

Navigate to the reporte page for a `review_required` or `high_risk` expediente. Verify:
- Each ActionCard shows numbered steps, not just one sentence
- SAT factors show a "Verificar en sat.gob.mx" link
- Critical factors have the legal_ref section expanded by default

- [ ] **Step 5: Smoke test — review flow**

Open an expediente with at least 2 documents in `extracted` status. Click "Revisar" on the first doc. Confirm it. Verify the confirmation screen shows "X documentos más por revisar" and the "Revisar siguiente documento" button goes to the next one.

- [ ] **Step 6: Create PR**

```bash
gh pr create \
  --base main \
  --title "fix: upload 500 (RLS/filesystem), consultas_sat column, UX polish" \
  --body "$(cat <<'EOF'
## Summary
- Fix POST /documentos 500 — replace broken 3-step signed-URL flow with single server-side upload+extract endpoint (bypasses Storage RLS)
- Fix POST /documentos/{id}/extract 500 — no longer reads local filesystem; extraction is now inline in /upload
- Fix GET /expedientes/{id}/consultas-sat 500 — column is consulted_at, not created_at
- Block duplicate doc_type uploads at backend (409) and handle gracefully in frontend
- ActionCard: per-factor-code specific steps + verifiable SAT links + urgency labels
- FactorDetailCard: legal_ref auto-expanded for critical/high-risk factors
- RevisarPage: next-document flow after confirming review
- SmartDropZone + DocumentUploader: router.refresh() after upload so server grid re-renders

## Test plan
- [ ] Upload a PDF → no 500 → document appears in grid
- [ ] Upload same PDF type again → graceful handling (no duplicate)
- [ ] Audit log SAT tab → 200, shows consultas
- [ ] Report actions → specific steps visible, SAT link present for sat_* factors
- [ ] Review doc → confirm → "next document" button visible if more docs need review
EOF
)"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|---|---|
| Upload 500 (StorageApiError RLS) | Task 2 |
| Extract 500 (local filesystem) | Task 2 (inline in upload) |
| consultas_sat.created_at → consulted_at | Task 1 |
| Document deduplication | Task 2 (409 guard) + Task 4 (graceful handle) |
| SmartDropZone broken 3-step → 1-step | Task 4 |
| DocumentUploader broken 3-step → 1-step | Task 5 |
| ActionCard enrichment with specific steps | Task 6 |
| Legal refs visible for critical factors | Task 7 |
| Review next-document flow | Task 8 |
| Deploy + smoke test | Task 9 |

### Placeholder Scan

No TBDs, TODOs, or "similar to Task N" references. All code blocks are complete and standalone.

### Type Consistency

- `DuplicateDocumentoError` defined in Task 3, used in Tasks 4 and 5 — consistent.
- `UploadDocumentoResult` defined in Task 3, returned by `api.uploadDocumento`, consumed in SmartDropZone and DocumentUploader — consistent.
- `FactorDetail.factor_code` used as key in `FACTOR_ACTIONS` (Task 6) — matches the type defined in `api-client.ts`.
- `router.refresh()` calls in Tasks 4 and 5 — `useRouter` already imported in both components.
- `remainingDocs` state added in Task 8 — `useState` already imported in `revisar/page.tsx`.
