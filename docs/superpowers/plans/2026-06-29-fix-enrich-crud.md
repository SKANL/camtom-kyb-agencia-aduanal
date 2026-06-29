# Fix + Enrich + CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 silent bugs (audit SAT field names, server-component cache, socios raw JSON, art_69b_bis silence), add PATCH/DELETE expediente CRUD, enrich the KYB reporte with SAT audit evidence + plain-language decision narrative, and delete stale demo data so the platform starts fresh.

**Architecture:** Backend gets two new REST endpoints (PATCH + DELETE) with TDD. Frontend fixes are split by concern: api-client cache config, audit SAT field names, socios structured input, ExpedienteActions client component for edit/delete dialogs, and report enrichment (SatEvidenceSection component + decision narrative). No new pages — all changes land in existing files plus 2 new client components.

**Tech Stack:** FastAPI + Supabase (Python 3.13, uv), Next.js 15 App Router (TypeScript, pnpm), shadcn/ui (@base-ui/react Dialog), Tailwind CSS, Lucide icons.

## Global Constraints

- Python 3.13; run tests with `cd backend && uv run pytest src/tests/ -v` — never bare `pytest`
- `pnpm` only in `frontend/` — never npm/yarn
- TDD for all backend changes: write failing test → implement → verify green
- All UI copy in Spanish; code identifiers and code comments in English
- Follow existing Tailwind + shadcn/ui patterns — import Dialog, Button, etc. from `@/components/ui/`
- Conventional commits only — no "Co-Authored-By"
- All FK constraints on `expedientes` are `ON DELETE CASCADE` — a single `DELETE` cascades to documentos, socios, consultas_sat, evaluations, audit_log
- Server-side fetches in Next.js App Router are cached by default; `cache: 'no-store'` opts out

---

## File Map

| File | Change |
|---|---|
| `backend/src/api/routers/expedientes.py` | Add `PATCH /{id}` and `DELETE /{id}` endpoints |
| `backend/src/tests/test_expedientes_router.py` | Add tests for PATCH and DELETE |
| `frontend/lib/api-client.ts` | Add `cache: 'no-store'`, `updateExpediente`, `deleteExpediente`, typed `ConsultaSat` |
| `frontend/app/expedientes/[id]/page.tsx` | Fix audit SAT field names; add `ExpedienteActions` |
| `frontend/app/expedientes/[id]/revisar/page.tsx` | Replace socios JSON textarea with structured list |
| `frontend/app/page.tsx` | Add `ExpedienteActions` per dashboard row; fix status labels |
| `frontend/app/expedientes/[id]/reporte/page.tsx` | Fetch consultas_sat; add SAT evidence section + narrative |
| `frontend/components/ExpedienteActions.tsx` | **NEW** — client component with edit + delete dialogs |
| `frontend/components/SatEvidenceSection.tsx` | **NEW** — SAT audit evidence table for reporte |

---

## Task 1: Backend — PATCH + DELETE expediente (TDD)

**Files:**
- Modify: `backend/src/api/routers/expedientes.py`
- Modify: `backend/src/tests/test_expedientes_router.py`

**Interfaces:**
- Produces:
  - `PATCH /expedientes/{expediente_id}` → `200 {updated expediente}` or `404`
  - `DELETE /expedientes/{expediente_id}` → `204 No Content` or `404`

- [ ] **Step 1: Write failing tests**

Append to `backend/src/tests/test_expedientes_router.py`:

```python
# ---------------------------------------------------------------------------
# PATCH /expedientes/{id}
# ---------------------------------------------------------------------------

def test_patch_expediente_updates_razon_social(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "abc-123", "razon_social": "Original SA", "rfc": "ORI010101AB1",
         "domicilio_fiscal": "", "representante_legal": "", "status": "pending",
         "decision": None, "score_total": None}
    ]
    response = client.patch("/expedientes/abc-123", json={"razon_social": "Nueva SA"})
    assert response.status_code == 200
    data = response.json()
    assert data["razon_social"] == "Nueva SA"


def test_patch_expediente_uppercases_rfc(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "abc-123", "razon_social": "X", "rfc": "OLD010101AB1",
         "domicilio_fiscal": "", "representante_legal": "", "status": "pending",
         "decision": None, "score_total": None}
    ]
    response = client.patch("/expedientes/abc-123", json={"rfc": "new010101ab1"})
    assert response.status_code == 200
    assert response.json()["rfc"] == "NEW010101AB1"


def test_patch_expediente_returns_404_for_unknown_id(client, fake_supabase):
    response = client.patch("/expedientes/no-such-id", json={"razon_social": "X"})
    assert response.status_code == 404


def test_patch_expediente_rejects_empty_body(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "abc-123", "razon_social": "X", "rfc": "ABC010101AB1",
         "domicilio_fiscal": "", "representante_legal": "", "status": "pending",
         "decision": None, "score_total": None}
    ]
    response = client.patch("/expedientes/abc-123", json={})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /expedientes/{id}
# ---------------------------------------------------------------------------

def test_delete_expediente_returns_204(client, fake_supabase):
    fake_supabase.store["expedientes"] = [
        {"id": "del-123", "razon_social": "X", "rfc": "DEL010101AB1",
         "domicilio_fiscal": "", "representante_legal": "", "status": "pending",
         "decision": None, "score_total": None}
    ]
    response = client.delete("/expedientes/del-123")
    assert response.status_code == 204


def test_delete_expediente_returns_404_for_unknown_id(client, fake_supabase):
    response = client.delete("/expedientes/no-such-id")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest src/tests/test_expedientes_router.py -k "patch or delete" -v
```

Expected: 6 failures — `patch` and `delete` routes don't exist yet.

- [ ] **Step 3: Implement PATCH and DELETE in the router**

Add to `backend/src/api/routers/expedientes.py` after the `crear_expediente` route:

```python
class ActualizarExpedienteBody(BaseModel):
    razon_social: str | None = None
    rfc: str | None = None
    domicilio_fiscal: str | None = None
    representante_legal: str | None = None


@router.patch("/{expediente_id}")
def actualizar_expediente(
    expediente_id: str,
    body: ActualizarExpedienteBody,
    supabase: Client = Depends(get_supabase_client),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    if "rfc" in data:
        data["rfc"] = data["rfc"].upper()
    check = supabase.table("expedientes").select("id").eq("id", expediente_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    result = supabase.table("expedientes").update(data).eq("id", expediente_id).execute()
    if result.data:
        return result.data[0]
    # FakeSupabase update returns empty data — return the mutated store row for tests
    rows = supabase.table("expedientes").select("*").eq("id", expediente_id).execute()
    return rows.data[0]


@router.delete("/{expediente_id}", status_code=204)
def eliminar_expediente(
    expediente_id: str,
    supabase: Client = Depends(get_supabase_client),
):
    check = supabase.table("expedientes").select("id").eq("id", expediente_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    supabase.table("expedientes").delete().eq("id", expediente_id).execute()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest src/tests/test_expedientes_router.py -v
```

Expected: all tests GREEN including the 6 new ones.

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/api/routers/expedientes.py src/tests/test_expedientes_router.py
git commit -m "feat: add PATCH and DELETE /expedientes/{id} endpoints"
```

---

## Task 2: Frontend api-client — cache, new endpoints, typed ConsultaSat

**Files:**
- Modify: `frontend/lib/api-client.ts`

**Interfaces:**
- Produces:
  - `api.updateExpediente(id, data)` → `Promise<Expediente>`
  - `api.deleteExpediente(id)` → `Promise<void>`
  - `api.listConsultasSat(id)` → `Promise<ConsultaSat[]>`
  - All `request()` calls include `cache: 'no-store'` so `router.refresh()` sees fresh data

- [ ] **Step 1: Replace `frontend/lib/api-client.ts` with the updated version**

The file has the following key changes:
1. Add `cache: 'no-store'` to the `request()` function
2. Add `ConsultaSat` type (replacing the loose `unknown[]`)
3. Add `updateExpediente` and `deleteExpediente` to `api`

Full updated `frontend/lib/api-client.ts`:

```typescript
const RAW_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// El trailing slash de NEXT_PUBLIC_API_URL + el leading slash de cada path
// produce URL con // (ej: vercel.app//expedientes), que Vercel redirige y
// ese redirect rompe el preflight CORS. Normalizar a un solo slash.
const API_URL = RAW_API_URL.replace(/\/+$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
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

export type UploadDocumentoResult = {
  documento_id: string;
  extraction_status: string;
};

export type SatImportRun = {
  id: string;
  list_type: string;
  status: string;
  rows_imported: number | null;
  started_at: string | null;
  finished_at: string | null;
};

export type ConsultaSat = {
  id: string;
  expediente_id: string;
  list_type: string;
  rfc_consultado: string;
  found: boolean;
  match_substate: string | null;
  match_detail: Record<string, unknown> | null;
  consulted_at: string;
  import_run_id: string | null;
  source_url: string | null;
};

export class DuplicateDocumentoError extends Error {
  constructor(public readonly documentoId: string) {
    super("Documento duplicado");
  }
}

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

  updateExpediente: (
    id: string,
    data: {
      razon_social?: string;
      rfc?: string;
      domicilio_fiscal?: string;
      representante_legal?: string;
    }
  ): Promise<Expediente> =>
    request(`/expedientes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteExpediente: (id: string): Promise<void> =>
    request(`/expedientes/${id}`, { method: "DELETE" }),

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

  listConsultasSat: (expedienteId: string): Promise<ConsultaSat[]> =>
    request(`/expedientes/${expedienteId}/consultas-sat`),

  // Admin
  triggerSatImport: (listType: string): Promise<SatImportRun> =>
    request(`/admin/ingest/${listType}`, { method: "POST" }),

  listSatImportRuns: (): Promise<SatImportRun[]> =>
    request("/admin/sat-import-runs"),
};

// Backward compat for existing page.tsx
export async function checkHealth(): Promise<{ status: string }> {
  return api.checkHealth();
}
```

- [ ] **Step 2: Verify TypeScript compiles cleanly**

```bash
cd frontend && pnpm tsc --noEmit 2>&1 | head -40
```

Expected: no errors (or only pre-existing errors unrelated to api-client.ts).

- [ ] **Step 3: Commit**

```bash
cd frontend && git add lib/api-client.ts
git commit -m "feat: add updateExpediente, deleteExpediente, typed ConsultaSat; add cache: no-store"
```

---

## Task 3: Fix audit SAT tab + status labels in expediente detail

**Files:**
- Modify: `frontend/app/expedientes/[id]/page.tsx`

The current tab reads `c.resultado` (undefined) and `c.rfc` (undefined). The actual fields from the backend are `found` (boolean), `match_substate` (string|null), and `rfc_consultado`.

Also fix: the `status` field in the dashboard shows raw enum values (`pending`, `completed`) — change to Spanish labels.

- [ ] **Step 1: Update the ConsultaSat type import and fix audit tab rendering**

In `frontend/app/expedientes/[id]/page.tsx`, make these targeted changes:

**Change 1** — Add `ConsultaSat` to imports:
```typescript
import { api, type ConsultaSat } from "@/lib/api-client";
```

**Change 2** — Remove `RESULTADO_BADGE` constant (it was based on a field that doesn't exist) and replace with inline logic. Find and replace:

Remove this block entirely:
```typescript
const RESULTADO_BADGE: Record<string, { label: string; className: string }> = {
  sin_coincidencia: { label: "Sin coincidencia", className: "bg-success/15 text-success" },
  coincidencia: { label: "Coincidencia", className: "bg-destructive/15 text-destructive" },
  formato_invalido: { label: "RFC inválido", className: "bg-warning/15 text-warning" },
};
```

**Change 3** — Fix the type annotation on `consultasSat`:
```typescript
let consultasSat: ConsultaSat[] = [];
```

**Change 4** — Fix the audit tab `<TabsContent value="audit">` tbody. Replace the entire `{consultasSat.map(...)...}` block with:

```tsx
{consultasSat.map((c) => {
  const found = c.found;
  const substate = c.match_substate;
  let badgeClass = "bg-success/15 text-success";
  let badgeLabel = "Sin coincidencia";
  if (found && substate === "definitivo") {
    badgeClass = "bg-destructive text-background";
    badgeLabel = "EFOS Definitivo";
  } else if (found && substate === "presunto") {
    badgeClass = "bg-destructive/15 text-destructive";
    badgeLabel = "EFOS Presunto";
  } else if (found) {
    badgeClass = "bg-warning/15 text-warning";
    badgeLabel = `Encontrado — ${substate ?? "coincidencia"}`;
  }
  return (
    <tr key={c.id} className="border-t border-border">
      <td className="px-3 py-2">
        {LIST_TYPE_LABELS[c.list_type] ?? c.list_type ?? "—"}
      </td>
      <td className="px-3 py-2 font-mono text-xs">{c.rfc_consultado ?? "—"}</td>
      <td className="px-3 py-2">
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${badgeClass}`}>
          {badgeLabel}
        </span>
      </td>
      <td className="px-3 py-2 text-right text-xs">
        {c.consulted_at
          ? new Date(c.consulted_at).toLocaleString("es-MX")
          : "—"}
      </td>
    </tr>
  );
})}
```

- [ ] **Step 2: Verify the app renders without TypeScript errors**

```bash
cd frontend && pnpm tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add app/expedientes/\[id\]/page.tsx
git commit -m "fix: correct consultas_sat field names in audit tab (found/match_substate/rfc_consultado)"
```

---

## Task 4: Fix socios structured display in revisar page

**Files:**
- Modify: `frontend/app/expedientes/[id]/revisar/page.tsx`

Currently the `socios` field is rendered as a raw JSON textarea. For non-technical users this is incomprehensible. Replace with a structured socio list: one card per socio with individual inputs for `nombre`, `rfc`, `porcentaje`, plus an "Add socio" button.

- [ ] **Step 1: Replace the socios rendering block**

In `revisar/page.tsx`, find the existing field rendering inside the `Object.entries(fields).map(...)` callback. Currently `socios` falls through to the generic `<Textarea>` case because only `declara_no_69b_49bis` has a special case.

Add a new case for `socios` BEFORE the generic textarea fallback. The new rendering block goes inside the `.map()` callback, after the `declara_no_69b_49bis` branch:

```tsx
if (campo === "socios") {
  let sociosList: Array<{ nombre?: string; rfc?: string; porcentaje?: string | number }> = [];
  try {
    const parsed = JSON.parse(valor);
    if (Array.isArray(parsed)) sociosList = parsed;
  } catch {
    // malformed — start fresh
  }

  function updateSocio(
    idx: number,
    field: "nombre" | "rfc" | "porcentaje",
    val: string
  ) {
    const updated = sociosList.map((s, i) =>
      i === idx ? { ...s, [field]: field === "porcentaje" ? val : val } : s
    );
    setFields({ ...fields, socios: JSON.stringify(updated) });
  }

  function addSocio() {
    const updated = [...sociosList, { nombre: "", rfc: "", porcentaje: "" }];
    setFields({ ...fields, socios: JSON.stringify(updated) });
  }

  function removeSocio(idx: number) {
    const updated = sociosList.filter((_, i) => i !== idx);
    setFields({ ...fields, socios: JSON.stringify(updated) });
  }

  return (
    <div key={campo}>
      <label className="text-xs text-muted-foreground block mb-2">
        {FIELD_LABELS[campo] ?? campo}
      </label>
      <div className="space-y-3">
        {sociosList.length === 0 && (
          <p className="text-xs text-muted-foreground">Sin socios registrados aún.</p>
        )}
        {sociosList.map((socio, idx) => (
          <div
            key={idx}
            className="rounded-lg border border-border bg-muted/30 p-3 space-y-2"
          >
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-semibold text-muted-foreground">
                Socio / Accionista {idx + 1}
              </p>
              <button
                type="button"
                onClick={() => removeSocio(idx)}
                className="text-xs text-destructive hover:underline"
              >
                Eliminar
              </button>
            </div>
            {(
              [
                { field: "nombre", label: "Nombre completo" },
                { field: "rfc", label: "RFC" },
                { field: "porcentaje", label: "Participación (%)" },
              ] as const
            ).map(({ field, label }) => (
              <div key={field}>
                <label className="text-xs text-muted-foreground block mb-0.5">
                  {label}
                </label>
                <input
                  type="text"
                  value={String(socio[field] ?? "")}
                  onChange={(e) => updateSocio(idx, field, e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            ))}
          </div>
        ))}
        <button
          type="button"
          onClick={addSocio}
          className="text-xs text-primary hover:underline font-medium"
        >
          + Agregar socio / accionista
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add "app/expedientes/[id]/revisar/page.tsx"
git commit -m "fix: replace socios raw JSON textarea with structured socio list in revisar"
```

---

## Task 5: ExpedienteActions client component (edit + delete dialogs)

**Files:**
- Create: `frontend/components/ExpedienteActions.tsx`

This is a pure client component that renders two icon buttons (edit pencil, delete trash) and manages two controlled dialogs: one for editing the 4 expediente fields, one for confirming the delete. It calls `api.updateExpediente` / `api.deleteExpediente` and then `router.refresh()` or `router.push("/")`.

- [ ] **Step 1: Create `frontend/components/ExpedienteActions.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Pencil, Trash2 } from "lucide-react";
import { api, type Expediente } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

type Props = {
  expediente: Pick<
    Expediente,
    "id" | "razon_social" | "rfc" | "domicilio_fiscal" | "representante_legal"
  >;
  redirectOnDelete?: boolean;
};

export function ExpedienteActions({
  expediente,
  redirectOnDelete = false,
}: Props) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    razon_social: expediente.razon_social,
    rfc: expediente.rfc,
    domicilio_fiscal: expediente.domicilio_fiscal ?? "",
    representante_legal: expediente.representante_legal ?? "",
  });

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await api.updateExpediente(expediente.id, form);
      setEditOpen(false);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await api.deleteExpediente(expediente.id);
      if (redirectOnDelete) {
        router.push("/");
      } else {
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
      setDeleting(false);
    }
  }

  const fields: { key: keyof typeof form; label: string }[] = [
    { key: "razon_social", label: "Razón social" },
    { key: "rfc", label: "RFC" },
    { key: "domicilio_fiscal", label: "Domicilio fiscal" },
    { key: "representante_legal", label: "Representante legal" },
  ];

  return (
    <>
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => { setError(null); setEditOpen(true); }}
          title="Editar expediente"
        >
          <Pencil className="size-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => { setError(null); setDeleteOpen(true); }}
          title="Eliminar expediente"
        >
          <Trash2 className="size-3.5 text-destructive" />
        </Button>
      </div>

      {/* Edit dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Editar expediente</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            {fields.map(({ key, label }) => (
              <div key={key}>
                <label className="text-xs text-muted-foreground block mb-1">
                  {label}
                </label>
                <input
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  value={form[key]}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, [key]: e.target.value }))
                  }
                />
              </div>
            ))}
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Guardando…" : "Guardar cambios"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Eliminar expediente</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground py-2">
            Esto eliminará permanentemente el expediente de{" "}
            <strong className="text-foreground">
              {expediente.razon_social}
            </strong>{" "}
            junto con todos sus documentos, evaluaciones y consultas SAT. Esta
            acción no se puede deshacer.
          </p>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              disabled={deleting}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Eliminando…" : "Eliminar expediente"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && pnpm tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add components/ExpedienteActions.tsx
git commit -m "feat: add ExpedienteActions client component with edit and delete dialogs"
```

---

## Task 6: Dashboard + expediente detail — integrate ExpedienteActions

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/expedientes/[id]/page.tsx`

- [ ] **Step 1: Update dashboard (`app/page.tsx`)**

**Change 1** — Add import at the top of the file:
```tsx
import { ExpedienteActions } from "@/components/ExpedienteActions";
```

**Change 2** — Add a status label map (after the DECISION_BADGE constant):
```tsx
const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  processing: "Procesando",
  completed: "Completado",
  needs_update: "Requiere actualización",
};
```

**Change 3** — In the table `<thead>`, add an "Acciones" column header after the "Score" `<th>`:
```tsx
<th className="text-right px-4 py-3 text-muted-foreground font-medium">Acciones</th>
```

**Change 4** — In the table `<tbody>`, replace the status `<td>` value with Spanish label:
```tsx
<td className="px-4 py-3 text-muted-foreground text-xs">
  {STATUS_LABEL[e.status] ?? e.status}
</td>
```

**Change 5** — Add a new `<td>` at the end of each row (after the score `<td>`):
```tsx
<td className="px-4 py-3 text-right">
  <ExpedienteActions expediente={e} redirectOnDelete={false} />
</td>
```

- [ ] **Step 2: Update expediente detail (`app/expedientes/[id]/page.tsx`)**

**Change 1** — Add import:
```tsx
import { ExpedienteActions } from "@/components/ExpedienteActions";
```

**Change 2** — In the header section, find the `<div className="flex items-start justify-between gap-4 mt-2">` block. After the `<div>` containing `<h1>` and `<p>` (razón social + RFC), and before the "Ver reporte KYB →" Link, insert:
```tsx
<div className="flex items-center gap-2 shrink-0">
  <ExpedienteActions expediente={expediente} redirectOnDelete={true} />
  <Link
    href={`/expedientes/${id}/reporte`}
    className="inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all"
  >
    Ver reporte KYB →
  </Link>
</div>
```

Remove the old standalone Link that was there before.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && pnpm tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
cd frontend && git add app/page.tsx "app/expedientes/[id]/page.tsx"
git commit -m "feat: add edit/delete actions to dashboard and expediente detail"
```

---

## Task 7: SatEvidenceSection component + report enrichment

**Files:**
- Create: `frontend/components/SatEvidenceSection.tsx`
- Modify: `frontend/app/expedientes/[id]/reporte/page.tsx`

This task adds two things to the reporte:
1. A "Evidencia de consultas SAT" section showing the actual audit trail (which lists were queried, when, and what was found)
2. A plain-language decision narrative explaining WHY the system reached its verdict

- [ ] **Step 1: Create `frontend/components/SatEvidenceSection.tsx`**

```tsx
import type { ConsultaSat } from "@/lib/api-client";
import { ShieldCheck, ShieldAlert, Clock } from "lucide-react";

const LIST_LABELS: Record<string, { label: string; description: string }> = {
  art_69: {
    label: "Art. 69 CFF",
    description: "Contribuyentes con obligaciones fiscales incumplidas",
  },
  art_69b: {
    label: "Art. 69-B CFF",
    description: "EFOS — Empresas que Facturan Operaciones Simuladas",
  },
  art_69b_bis: {
    label: "Art. 69-B Bis CFF",
    description: "Transmisión indebida de pérdidas fiscales",
  },
};

const SUBSTATE_LABELS: Record<string, string> = {
  definitivo: "Definitivo",
  presunto: "Presunto",
  desvirtuado: "Desvirtuado",
  sentencia_favorable: "Sentencia favorable",
};

type Props = {
  consultas: ConsultaSat[];
};

export function SatEvidenceSection({ consultas }: Props) {
  if (consultas.length === 0) return null;

  // Dedupe: show the most recent consulta per list_type
  const byList: Record<string, ConsultaSat> = {};
  for (const c of consultas) {
    if (
      !byList[c.list_type] ||
      new Date(c.consulted_at) > new Date(byList[c.list_type].consulted_at)
    ) {
      byList[c.list_type] = c;
    }
  }
  const latest = Object.values(byList);

  const anyFound = latest.some((c) => c.found);

  return (
    <section className="mb-6">
      <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
        Evidencia de consultas SAT
      </h2>
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center gap-2">
          {anyFound ? (
            <ShieldAlert className="size-4 text-destructive shrink-0" />
          ) : (
            <ShieldCheck className="size-4 text-success shrink-0" />
          )}
          <p className="text-xs text-muted-foreground">
            Se consultaron{" "}
            <strong className="text-foreground">{latest.length} listas fiscales</strong>{" "}
            del SAT en tiempo real contra la base de datos local
            {latest[0]?.rfc_consultado && (
              <>
                {" "}para el RFC{" "}
                <span className="font-mono font-semibold text-foreground">
                  {latest[0].rfc_consultado}
                </span>
              </>
            )}.
          </p>
        </div>

        <div className="divide-y divide-border">
          {latest.map((c) => {
            const listInfo = LIST_LABELS[c.list_type];
            const found = c.found;
            const substate = c.match_substate;

            return (
              <div key={c.id} className="px-4 py-3 flex items-start gap-4">
                <div className="mt-0.5 shrink-0">
                  {found ? (
                    <ShieldAlert className="size-4 text-destructive" />
                  ) : (
                    <ShieldCheck className="size-4 text-success" />
                  )}
                </div>
                <div className="flex-1 min-w-0 space-y-0.5">
                  <p className="text-sm font-semibold">
                    {listInfo?.label ?? c.list_type}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {listInfo?.description ?? ""}
                  </p>
                  {found && substate && (
                    <div className="mt-1">
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-destructive text-background">
                        {SUBSTATE_LABELS[substate] ?? substate}
                      </span>
                    </div>
                  )}
                </div>
                <div className="shrink-0 text-right space-y-0.5">
                  <div>
                    {found ? (
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-destructive/15 text-destructive">
                        Encontrado
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-success/15 text-success">
                        Sin coincidencia
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 justify-end text-xs text-muted-foreground">
                    <Clock className="size-3" />
                    <span>
                      {new Date(c.consulted_at).toLocaleString("es-MX", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Add decision narrative function to `reporte/page.tsx`**

At the top of the file (after imports), add this pure function — it generates a 2-3 sentence plain-language narrative based on the evaluation:

```tsx
function buildNarrative(
  decision: string,
  scoreTotal: number,
  factores: { factor_code: string; is_critical_block: boolean; points: number }[]
): string {
  const hasCritical = factores.some((f) => f.is_critical_block);
  const critFactor = factores.find((f) => f.is_critical_block);
  const topFactor = [...factores].sort((a, b) => b.points - a.points)[0];

  if (decision === "high_risk") {
    if (hasCritical && critFactor) {
      const critLabels: Record<string, string> = {
        sat_69b_definitivo: "el RFC fue localizado en el listado definitivo de EFOS (Art. 69-B CFF)",
      };
      const reason = critLabels[critFactor.factor_code] ?? `el factor "${critFactor.factor_code}" activó un bloqueo crítico`;
      return `La operación está bloqueada porque ${reason}. Este hallazgo es un bloqueo directo e incondicional — independientemente de cualquier otro factor, el RFC no puede operar en comercio exterior hasta obtener resolución formal del SAT. Se requiere acción inmediata antes de continuar cualquier trámite.`;
    }
    return `El expediente acumuló ${scoreTotal} puntos de riesgo — por encima del umbral de 100 que define la clasificación de alto riesgo. El factor de mayor impacto fue "${topFactor?.factor_code ?? "desconocido"}" con ${topFactor?.points ?? 0} puntos. Se requiere resolver los factores críticos antes de proceder a la inscripción en el padrón.`;
  }

  if (decision === "review_required") {
    return `El expediente acumuló ${scoreTotal} puntos de riesgo (umbral de revisión: 50–99 puntos). No se detectaron bloqueos críticos, pero hay inconsistencias o datos faltantes que impiden aprobar la operación de forma automática. El agente aduanal debe revisar y resolver cada factor antes de emitir una recomendación final.`;
  }

  if (decision === "safe") {
    return `El expediente acumuló ${scoreTotal} puntos de riesgo — por debajo del umbral de 50 que define la clasificación segura. No se encontraron coincidencias en listas fiscales del SAT, los documentos están completos y los datos son consistentes entre sí. El RFC puede proceder a la inscripción en el padrón de importadores/exportadores.`;
  }

  return "La evaluación está en curso. Cargá todos los documentos requeridos y ejecutá la evaluación KYB para obtener el reporte completo.";
}
```

- [ ] **Step 3: Update `reporte/page.tsx` — fetch consultas_sat + render narrative + evidence**

**Change 1** — Update the data fetch block to also load `consultasSat`:

```tsx
let expediente = null;
let evaluation = null;
let consultasSat: import("@/lib/api-client").ConsultaSat[] = [];
try {
  [expediente, evaluation, consultasSat] = await Promise.all([
    api.getExpediente(id),
    api.getLatestEvaluation(id).catch(() => null),
    api.listConsultasSat(id).catch(() => []),
  ]);
} catch {
  // Build time
}
```

**Change 2** — Add `SatEvidenceSection` import at the top:
```tsx
import { SatEvidenceSection } from "@/components/SatEvidenceSection";
```

**Change 3** — After the `<DecisionContext>` block (which is already present), add the narrative paragraph and SAT evidence section. Insert this BEFORE the "Risk factors" section:

```tsx
{/* Decision narrative */}
{evaluation && (
  <div className="rounded-xl border border-border bg-card p-5 mb-6 space-y-2">
    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
      ¿Por qué esta decisión?
    </p>
    <p className="text-sm text-foreground/90 leading-relaxed">
      {buildNarrative(evaluation.decision, evaluation.score_total, factoresDetail)}
    </p>
    <details className="pt-1">
      <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground select-none">
        Ver umbrales de clasificación
      </summary>
      <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
        <div className="rounded-lg bg-success/10 p-2 text-center">
          <p className="font-bold text-success">0 – 49 pts</p>
          <p className="text-muted-foreground mt-0.5">Seguro</p>
        </div>
        <div className="rounded-lg bg-warning/10 p-2 text-center">
          <p className="font-bold text-warning">50 – 99 pts</p>
          <p className="text-muted-foreground mt-0.5">Revisión requerida</p>
        </div>
        <div className="rounded-lg bg-destructive/10 p-2 text-center">
          <p className="font-bold text-destructive">100+ pts</p>
          <p className="text-muted-foreground mt-0.5">Alto riesgo</p>
        </div>
      </div>
    </details>
  </div>
)}

{/* SAT evidence */}
{consultasSat.length > 0 && (
  <SatEvidenceSection consultas={consultasSat} />
)}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && pnpm tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 5: Commit**

```bash
cd frontend && git add components/SatEvidenceSection.tsx "app/expedientes/[id]/reporte/page.tsx"
git commit -m "feat: add SAT evidence section and decision narrative to KYB report"
```

---

## Task 8: Data cleanup — delete all expedientes

**Action:** Delete all 4 existing expedientes via Supabase MCP. All FK constraints have `ON DELETE CASCADE`, so documentos, evaluations, consultas_sat, socios, and audit_log rows cascade automatically.

- [ ] **Step 1: Execute the DELETE via Supabase MCP**

Run this SQL against project `ssewwqhfcmpajjbnrlja`:

```sql
DELETE FROM expedientes;
```

- [ ] **Step 2: Verify the database is clean**

```sql
SELECT
  (SELECT COUNT(*) FROM expedientes) AS expedientes,
  (SELECT COUNT(*) FROM documentos) AS documentos,
  (SELECT COUNT(*) FROM evaluations) AS evaluations,
  (SELECT COUNT(*) FROM consultas_sat) AS consultas_sat;
```

Expected: all zeros. `sat_lista_registros` (578K rows) is NOT touched — it is the reference data.

- [ ] **Step 3: No commit needed** — this is a database operation, not a code change.

---

## Self-Review

### Spec coverage

| Requirement | Task |
|---|---|
| Fix audit SAT field names (found/match_substate/rfc_consultado) | Task 3 |
| Fix server component cache (no-store) | Task 2 |
| Fix socios raw JSON display | Task 4 |
| Add PATCH /expedientes/{id} | Task 1 |
| Add DELETE /expedientes/{id} | Task 1 |
| Edit expediente UI (dashboard + detail) | Tasks 5 + 6 |
| Delete expediente UI (dashboard + detail) | Tasks 5 + 6 |
| Dashboard status in Spanish | Task 6 |
| SAT evidence section in reporte | Task 7 |
| Decision narrative in reporte | Task 7 |
| Score threshold explanation | Task 7 |
| Delete stale expedientes | Task 8 |

### Placeholder scan

No TBD, TODO, or incomplete steps. Every step has concrete code or commands.

### Type consistency

- `ConsultaSat` type defined in `api-client.ts` (Task 2) and imported in `SatEvidenceSection.tsx` (Task 7)
- `api.updateExpediente` / `api.deleteExpediente` defined in Task 2, consumed in Task 5
- `api.listConsultasSat` return type changed to `ConsultaSat[]` in Task 2, used in Task 7
- `ExpedienteActions` props use `Pick<Expediente, ...>` — all fields come from existing `Expediente` type
