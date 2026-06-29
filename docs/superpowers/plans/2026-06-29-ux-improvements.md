# KYB UX/UI Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all critical bugs (upload failures, broken drag-drop), replace emojis with SVG icons, complete all user flows, and deliver a rich KYB report with regulatory citations, score breakdowns, and human-readable evidence.

**Architecture:** Pure frontend changes (Next.js App Router + Tailwind + Lucide React) plus one already-applied Supabase migration (kyb-docs bucket created). Backend unchanged — all data is already available in `factores_detail[].evidence`, `legal_ref`, and `category`. The report page fetches server-side, all interactive components are client components.

**Tech Stack:** Next.js 15 App Router, TypeScript, Tailwind CSS v4, shadcn/ui (base theme), Lucide React (icons), Supabase (already migrated — `kyb-docs` bucket exists)

## Global Constraints

- `pnpm` exclusively in `frontend/` — never npm/yarn
- Lucide React already installed — use it for ALL icons, no emojis in any UI
- Tailwind CSS v4 syntax — use `bg-success`, `bg-warning`, `bg-destructive`, `text-primary` etc.
- Never show raw JSON (`JSON.stringify`) to the user in any UI surface
- All UI copy in Spanish (Mexican, professional — no Rioplatense slang in code/UI)
- Current branch: `feat/ux-improvements` — commit to this branch
- Conventional commits only, no Co-Authored-By

---

## File Map

**Modified:**
- `frontend/components/SmartDropZone.tsx` — fix folder drag, stale closure, emojis→icons, post-upload CTA
- `frontend/components/FactorDetailCard.tsx` — human-readable evidence, SVG icons
- `frontend/components/ScoreGauge.tsx` — score explanation, category breakdown props
- `frontend/components/StepperHeader.tsx` — steps become clickable links when navigable
- `frontend/app/page.tsx` — fix row links (pending→expediente, evaluated→reporte)
- `frontend/app/expedientes/[id]/page.tsx` — show required docs checklist before any upload; fix `onAllDone` to refresh server data
- `frontend/app/expedientes/[id]/reporte/page.tsx` — score breakdown section, decision context panel, rich action cards

**Created:**
- `frontend/components/ScoreBreakdown.tsx` — score subtotals by category (SAT / Discrepancias / Completitud)
- `frontend/components/DecisionContext.tsx` — plain-language decision explanation + operational implications
- `frontend/components/ActionCard.tsx` — rich action card with icon, regulatory basis, and priority
- `backend/scripts/generate_demo_pdfs.py` — generates 3 text-selectable PDFs for demo

---

## Task 1 (DONE): Create kyb-docs Supabase storage bucket

Already applied via migration `create_kyb_docs_bucket`. Bucket exists with:
- `id = 'kyb-docs'`, `public = false`, `file_size_limit = 10485760` (10 MB)
- RLS: anon INSERT allowed (for signed URL uploads), service role reads unrestricted

---

## Task 2: Fix SmartDropZone — folder drag, stale closure, icons, post-upload CTA

**Files:**
- Modify: `frontend/components/SmartDropZone.tsx`

**Context:**
- Bug 1: `e.dataTransfer.files` is empty when a folder is dropped. Fix: use `e.dataTransfer.items` → `item.webkitGetAsEntry()` → recursive traversal to collect PDFs.
- Bug 2: `const startIdx = files.length` uses stale closure. Fix: match results back to pending by `key` (not array index).
- Bug 3: All emojis must become Lucide icons.
- UX gap: after all files are processed (`allProcessed`), show a card with two buttons: "Revisar campos extraídos" (links to first extractable doc) and "Ejecutar evaluación KYB" (calls `api.evaluate` then navigates to `/reporte`).

- [ ] **Step 1: Replace SmartDropZone with fixed version**

```tsx
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FolderOpen, CheckCircle2, XCircle, Loader2, AlertTriangle, X, ChevronRight, FileText,
} from "lucide-react";
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
  key: string;
  file: File;
  status: "classifying" | "classified" | "uploading" | "extracting" | "done" | "error";
  docType: string;
  confidence: "high" | "low";
  suggestedLabel: string;
  errorMsg?: string;
  documentoId?: string;
};

type Props = {
  expedienteId: string;
  existingDocTypes: string[];
  onAllDone?: () => void;
};

async function collectPdfs(entry: FileSystemEntry): Promise<File[]> {
  if (entry.isFile) {
    const fe = entry as FileSystemFileEntry;
    return new Promise((resolve) => {
      fe.file((f) => {
        if (f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")) {
          resolve([f]);
        } else {
          resolve([]);
        }
      });
    });
  }
  if (entry.isDirectory) {
    const de = entry as FileSystemDirectoryEntry;
    const reader = de.createReader();
    return new Promise((resolve) => {
      reader.readEntries(async (entries) => {
        const nested = await Promise.all(entries.map(collectPdfs));
        resolve(nested.flat());
      });
    });
  }
  return [];
}

export function SmartDropZone({ expedienteId, existingDocTypes, onAllDone = () => {} }: Props) {
  const router = useRouter();
  const [files, setFiles] = useState<FileState[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const classifyFiles = useCallback(async (newFiles: File[]) => {
    const pdfs = newFiles.filter(
      (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
    );
    if (!pdfs.length) return;

    const pending: FileState[] = pdfs.map((f) => ({
      key: `${f.name}-${f.lastModified}-${Math.random()}`,
      file: f,
      status: "classifying",
      docType: "unknown",
      confidence: "low",
      suggestedLabel: "Clasificando...",
    }));

    // Capture keys before the async gap so we can match results back
    const pendingKeys = pending.map((p) => p.key);
    setFiles((prev) => [...prev, ...pending]);

    const results = await Promise.all(
      pdfs.map((f) =>
        api.classifyDocumento(f).catch(() => ({
          doc_type: "unknown" as const,
          confidence: "low" as const,
          suggested_label: "Sin clasificar",
        }))
      )
    );

    setFiles((prev) => {
      const next = [...prev];
      results.forEach((result, i) => {
        const key = pendingKeys[i];
        const idx = next.findIndex((f) => f.key === key);
        if (idx !== -1) {
          next[idx] = {
            ...next[idx],
            status: "classified",
            docType: result.doc_type,
            confidence: result.confidence,
            suggestedLabel: result.suggested_label,
          };
        }
      });
      return next;
    });
  }, []);

  async function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    // Use items API to support folder drops
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      const entries = Array.from(e.dataTransfer.items)
        .map((item) => item.webkitGetAsEntry())
        .filter((entry): entry is FileSystemEntry => entry !== null);
      const allFiles = (await Promise.all(entries.map(collectPdfs))).flat();
      if (allFiles.length) {
        classifyFiles(allFiles);
        return;
      }
    }
    classifyFiles(Array.from(e.dataTransfer.files));
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      classifyFiles(Array.from(e.target.files));
      e.target.value = "";
    }
  }

  function setDocType(key: string, docType: string) {
    const label = DOC_TYPE_OPTIONS.find((o) => o.value === docType)?.label ?? "Sin clasificar";
    setFiles((prev) =>
      prev.map((f) => f.key === key ? { ...f, docType, suggestedLabel: label, confidence: "high" } : f)
    );
  }

  function removeFile(key: string) {
    setFiles((prev) => prev.filter((f) => f.key !== key));
  }

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
          const { documento_id, signed_url } = await api.crearDocumento(expedienteId, docType, "uploaded");
          if (signed_url) {
            await fetch(signed_url, { method: "PUT", body: file });
          }
          update("extracting", { documentoId: documento_id });
          await api.extractDocumento(documento_id);
          update("done", { documentoId: documento_id });
        } catch (err) {
          update("error", { errorMsg: err instanceof Error ? err.message : "Error al procesar" });
        }
      })
    );

    setProcessing(false);
  }

  async function handleEvaluate() {
    setEvaluating(true);
    try {
      await api.evaluate(expedienteId);
      router.push(`/expedientes/${expedienteId}/reporte`);
    } catch {
      setEvaluating(false);
    }
  }

  useEffect(() => {
    if (files.length > 0 && files.every((f) => f.status === "done" || f.status === "error")) {
      onAllDone();
    }
  }, [files, onAllDone]);

  const readyToProcess = files.some((f) => f.status === "classified" && f.docType !== "unknown");
  const allProcessed = files.length > 0 && files.every((f) => f.status === "done" || f.status === "error");
  const firstExtractableDocId = files.find((f) => f.status === "done" && f.documentoId)?.documentoId;

  function StatusIcon({ f }: { f: FileState }) {
    if (f.status === "done") return <CheckCircle2 className="size-4 text-success shrink-0" />;
    if (f.status === "error") return <XCircle className="size-4 text-destructive shrink-0" />;
    if (f.status === "classifying" || f.status === "uploading" || f.status === "extracting")
      return <Loader2 className="size-4 text-muted-foreground shrink-0 animate-spin" />;
    if (f.confidence === "high") return <CheckCircle2 className="size-4 text-primary shrink-0" />;
    return <AlertTriangle className="size-4 text-warning shrink-0" />;
  }

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
        <div className="flex justify-center">
          <FolderOpen className="size-10 text-muted-foreground" />
        </div>
        <p className="font-medium text-sm">
          Arrastrá tus PDFs aquí, o hacé clic para seleccionar
        </p>
        <p className="text-xs text-muted-foreground">
          Podés soltar una carpeta completa — la IA clasifica cada archivo automáticamente
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
          {files.map((f) => (
            <div
              key={f.key}
              className={[
                "rounded-lg border p-3 flex items-center gap-3 text-sm",
                f.status === "done"
                  ? "border-success/40 bg-success/5"
                  : f.status === "error"
                  ? "border-destructive/40 bg-destructive/5"
                  : "border-border bg-card",
              ].join(" ")}
            >
              <StatusIcon f={f} />

              <FileText className="size-3.5 text-muted-foreground shrink-0" />
              <span className="font-mono text-xs text-muted-foreground truncate min-w-0 flex-1">
                {f.file.name}
              </span>

              {f.status === "classified" ? (
                <select
                  value={f.docType}
                  onChange={(e) => setDocType(f.key, e.target.value)}
                  className="text-xs rounded-md border border-border bg-background px-2 py-1 shrink-0"
                >
                  <option value="unknown">Sin clasificar</option>
                  {DOC_TYPE_OPTIONS.filter(
                    (o) => !existingDocTypes.includes(o.value) || o.value === f.docType
                  ).map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              ) : (
                <span className={[
                  "text-xs shrink-0",
                  f.status === "done" ? "text-success"
                    : f.status === "error" ? "text-destructive"
                    : "text-muted-foreground animate-pulse",
                ].join(" ")}>
                  {f.status === "error" ? f.errorMsg
                    : f.status === "classifying" ? "Clasificando con IA..."
                    : f.status === "uploading" ? "Subiendo..."
                    : f.status === "extracting" ? "Extrayendo campos con IA..."
                    : f.status === "done" ? "Procesado"
                    : ""}
                </span>
              )}

              {(f.status === "classified" || f.status === "error") && (
                <button
                  onClick={(e) => { e.stopPropagation(); removeFile(f.key); }}
                  className="text-muted-foreground hover:text-foreground shrink-0 ml-1"
                  aria-label="Eliminar"
                >
                  <X className="size-3.5" />
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
          className="w-full"
        >
          {processing ? (
            <><Loader2 className="size-4 mr-2 animate-spin" /> Procesando documentos...</>
          ) : (
            "Procesar todos los documentos"
          )}
        </Button>
      )}

      {/* Post-processing CTA */}
      {allProcessed && (
        <div className="rounded-xl border border-success/40 bg-success/5 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-5 text-success shrink-0" />
            <p className="text-sm font-semibold text-success">Todos los documentos procesados</p>
          </div>
          <p className="text-xs text-muted-foreground">
            La IA extrajo los campos de cada documento. Revisá y confirmá los datos antes de ejecutar la evaluación KYB.
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            {firstExtractableDocId && (
              <a
                href={`/expedientes/${expedienteId}/revisar?documento_id=${firstExtractableDocId}`}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted transition-all"
              >
                Revisar campos extraídos
                <ChevronRight className="size-4" />
              </a>
            )}
            <Button onClick={handleEvaluate} disabled={evaluating} className="flex-1 sm:flex-none">
              {evaluating ? (
                <><Loader2 className="size-4 mr-2 animate-spin" /> Evaluando...</>
              ) : (
                <>Ejecutar evaluación KYB <ChevronRight className="size-4 ml-1" /></>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify SmartDropZone builds**

```bash
cd frontend && pnpm build 2>&1 | tail -30
```
Expected: no TypeScript errors for SmartDropZone.tsx

- [ ] **Step 3: Commit**

```bash
git add frontend/components/SmartDropZone.tsx
git commit -m "fix: SmartDropZone — folder drag, stale closure, SVG icons, post-upload CTA"
```

---

## Task 3: Fix dashboard navigation + StepperHeader links + audit SAT tab

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/components/StepperHeader.tsx`
- Modify: `frontend/app/expedientes/[id]/page.tsx` (audit tab only)

**Context:**
- Dashboard: un-evaluated expedientes (`decision === null`) must link to `/expedientes/${id}` (document upload step), not `/expedientes/${id}/reporte`.
- StepperHeader: completed steps (n < currentStep) become `<Link>` elements so the user can navigate back.
- Audit SAT tab: `list_type` values like `art_69`, `art_69b`, `art_69b_bis` must render as human-readable labels. `resultado` values must render as badges.

- [ ] **Step 1: Fix dashboard row navigation in `frontend/app/page.tsx`**

Find the `<Link href={...}>` that wraps `e.razon_social` and change it:

```tsx
// Before (line ~74-78):
<Link
  href={`/expedientes/${e.id}/reporte`}
  className="hover:text-primary transition-colors"
>
  {e.razon_social}
</Link>

// After:
<Link
  href={e.decision ? `/expedientes/${e.id}/reporte` : `/expedientes/${e.id}`}
  className="hover:text-primary transition-colors"
>
  {e.razon_social}
</Link>
```

Also add a "Ver documentos" link in the row's action area. In the last `<td>` (score column) add a small icon link after the score:

```tsx
<td className="px-4 py-3 text-right font-mono text-sm">
  <div className="flex items-center justify-end gap-3">
    {e.score_total !== null ? (
      <span className="text-primary font-bold">{e.score_total} pts</span>
    ) : (
      <span className="text-muted-foreground">—</span>
    )}
    <Link
      href={e.decision ? `/expedientes/${e.id}/reporte` : `/expedientes/${e.id}`}
      className="text-muted-foreground hover:text-primary transition-colors"
      title={e.decision ? "Ver reporte" : "Cargar documentos"}
    >
      <ChevronRight className="size-4" />
    </Link>
  </div>
</td>
```

Add import at top of `page.tsx`:
```tsx
import { ChevronRight } from "lucide-react";
```

- [ ] **Step 2: Make StepperHeader steps clickable**

Replace `frontend/components/StepperHeader.tsx` entirely:

```tsx
import Link from "next/link";

const STEPS = [
  { n: 1, label: "Datos empresa", href: (id?: string) => "/expedientes/nuevo" },
  { n: 2, label: "Documentos",    href: (id?: string) => id ? `/expedientes/${id}` : "#" },
  { n: 3, label: "Revisión",      href: (id?: string) => id ? `/expedientes/${id}` : "#" },
  { n: 4, label: "Reporte KYB",   href: (id?: string) => id ? `/expedientes/${id}/reporte` : "#" },
] as const;

export function StepperHeader({
  currentStep,
  expedienteId,
}: {
  currentStep: 1 | 2 | 3 | 4;
  expedienteId?: string;
}) {
  return (
    <nav className="flex items-center gap-0 mb-8">
      {STEPS.map((step, i) => {
        const done = step.n < currentStep;
        const active = step.n === currentStep;
        const href = done ? step.href(expedienteId) : undefined;

        const circle = (
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
            {done ? (
              <svg viewBox="0 0 12 10" className="size-3 fill-none stroke-current stroke-2">
                <polyline points="1,5 4,8 11,1" />
              </svg>
            ) : (
              step.n
            )}
          </div>
        );

        return (
          <div key={step.n} className="flex items-center gap-0 flex-1 min-w-0">
            <div className="flex flex-col items-center gap-1 shrink-0">
              {href ? (
                <Link href={href} className="hover:opacity-80 transition-opacity">
                  {circle}
                </Link>
              ) : (
                circle
              )}
              <span
                className={[
                  "text-xs whitespace-nowrap",
                  active ? "text-primary font-medium" : done ? "text-foreground" : "text-muted-foreground",
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

- [ ] **Step 3: Update all StepperHeader usages to pass expedienteId**

In `frontend/app/expedientes/[id]/page.tsx` (line ~65):
```tsx
<StepperHeader currentStep={2} expedienteId={id} />
```

In `frontend/app/expedientes/[id]/reporte/page.tsx` (line ~127):
```tsx
<StepperHeader currentStep={4} expedienteId={id} />
```

In `frontend/app/expedientes/[id]/revisar/page.tsx` — add StepperHeader import and render at top of the returned JSX:
```tsx
import { StepperHeader } from "@/components/StepperHeader";
// Inside return, before the breadcrumb div:
<StepperHeader currentStep={3} expedienteId={id} />
```

`frontend/app/expedientes/nuevo/page.tsx` doesn't need expedienteId (step 1).

- [ ] **Step 4: Fix audit SAT tab in `frontend/app/expedientes/[id]/page.tsx`**

Add these label maps after the existing `EXTRACTION_STATUS_BADGE` constant (around line 25):

```tsx
const LIST_TYPE_LABELS: Record<string, string> = {
  art_69: "Art. 69 CFF — Incumplidos",
  art_69b: "Art. 69-B CFF — EFOS",
  art_69b_bis: "Art. 69-B Bis CFF — Pérdidas",
};

const RESULTADO_BADGE: Record<string, { label: string; className: string }> = {
  sin_coincidencia: { label: "Sin coincidencia", className: "bg-success/15 text-success" },
  coincidencia: { label: "Coincidencia", className: "bg-destructive/15 text-destructive" },
  formato_invalido: { label: "RFC inválido", className: "bg-warning/15 text-warning" },
};
```

In the audit table body, replace raw cell renders:
```tsx
<td className="px-3 py-2 font-mono text-xs">
  {LIST_TYPE_LABELS[(c as any).list_type] ?? (c as any).list_type ?? "—"}
</td>
<td className="px-3 py-2 font-mono text-xs">{(c as any).rfc ?? "—"}</td>
<td className="px-3 py-2">
  {(() => {
    const r = (c as any).resultado ?? "";
    const badge = RESULTADO_BADGE[r];
    return badge ? (
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}>
        {badge.label}
      </span>
    ) : (
      <span className="text-muted-foreground text-xs">{r || "—"}</span>
    );
  })()}
</td>
```

- [ ] **Step 5: Build check**

```bash
cd frontend && pnpm build 2>&1 | tail -30
```
Expected: no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/page.tsx frontend/components/StepperHeader.tsx frontend/app/expedientes/[id]/page.tsx frontend/app/expedientes/[id]/reporte/page.tsx frontend/app/expedientes/[id]/revisar/page.tsx
git commit -m "fix: dashboard navigation, clickable stepper, audit SAT human-readable labels"
```

---

## Task 4: Enrich KYB report — score breakdown, action cards, decision context, FactorDetailCard

**Files:**
- Modify: `frontend/components/FactorDetailCard.tsx`
- Modify: `frontend/components/ScoreGauge.tsx`
- Modify: `frontend/app/expedientes/[id]/reporte/page.tsx`
- Create: `frontend/components/ScoreBreakdown.tsx`
- Create: `frontend/components/DecisionContext.tsx`
- Create: `frontend/components/ActionCard.tsx`

**Context:**
The `EvaluationResult` returned by the API has:
- `factores_detail[].evidence` — e.g. `{"doc_type":"acta_constitutiva"}` or `{"manual_review_required":true}` — must NOT be shown as raw JSON
- `factores_detail[].legal_ref` — full regulatory text, already rich
- `factores_detail[].category` — "sat" | "discrepancia" | "completitud" | "otro"
- `factores_detail[].is_critical_block` — boolean
- `score_total` — raw sum (can exceed 100 when multiple factors hit)
- `decision` — "safe" | "review_required" | "high_risk"
- `acciones_sugeridas` — string array, currently one sentence per action

Decision thresholds (from engine.py): safe = score < 30, review_required = 30–69, high_risk = score >= 70 OR any `is_critical_block`.

### 4a: Fix FactorDetailCard — human-readable evidence, SVG icons

- [ ] **Step 1: Replace FactorDetailCard**

```tsx
import { AlertTriangle, CheckCircle2, ShieldAlert, BookOpen, ChevronDown } from "lucide-react";
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
  doc_expired: "Comprobante de domicilio vencido (más de 90 días)",
  csf_stale: "Constancia de Situación Fiscal desactualizada",
  doc_data_incomplete: "Campos obligatorios incompletos en documento",
  manifestacion_incompleta: "Manifestación bajo protesta incompleta",
  socios_incompletos: "Socios o beneficiario controlador no registrados",
  rep_legal_incompleto: "Representante legal sin nombre completo",
};

const DOC_TYPE_LABELS: Record<string, string> = {
  csf: "Constancia de Situación Fiscal",
  acta_constitutiva: "Acta Constitutiva",
  comprobante_domicilio: "Comprobante de Domicilio",
  identificacion_rep_legal: "Identificación del Representante Legal",
  poder_notarial: "Poder Notarial",
  encargo_conferido: "Encargo Conferido",
  manifestacion_protesta: "Manifestación bajo Protesta de Decir Verdad",
  rfc: "Comprobante de RFC",
};

const CATEGORY_CHIP: Record<string, { label: string; className: string }> = {
  sat: { label: "Listas SAT", className: "bg-destructive/15 text-destructive" },
  discrepancia: { label: "Discrepancia documental", className: "bg-warning/15 text-warning" },
  completitud: { label: "Completitud del expediente", className: "bg-primary/15 text-primary" },
  otro: { label: "Otro", className: "bg-muted text-muted-foreground" },
};

function EvidenceDisplay({ evidence }: { evidence: Record<string, unknown> }) {
  const entries = Object.entries(evidence);
  return (
    <div className="space-y-1">
      {entries.map(([k, v]) => {
        if (k === "doc_type" && typeof v === "string") {
          return (
            <p key={k} className="text-xs text-muted-foreground">
              Documento afectado: <span className="font-medium text-foreground">{DOC_TYPE_LABELS[v] ?? v}</span>
            </p>
          );
        }
        if (k === "manual_review_required" && v === true) {
          return (
            <p key={k} className="text-xs text-warning font-medium">
              Requiere revisión manual por el agente aduanal
            </p>
          );
        }
        if (k === "documento_id") {
          return (
            <p key={k} className="text-xs text-muted-foreground">
              Documento con campos incompletos — revisión manual recomendada
            </p>
          );
        }
        // Fallback for unknown keys: render as readable text, never raw JSON
        return (
          <p key={k} className="text-xs text-muted-foreground capitalize">
            {k.replace(/_/g, " ")}: <span className="font-medium text-foreground">{String(v)}</span>
          </p>
        );
      })}
    </div>
  );
}

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
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {isCritical && (
              <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold bg-destructive text-background">
                <ShieldAlert className="size-3" />
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
          <p className="text-xs text-muted-foreground">pts de riesgo</p>
        </div>
      </div>

      {/* Progress bar */}
      {factor.points > 0 && (
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full ${isCritical ? "bg-destructive" : "bg-warning"}`}
            style={{ width: `${barPct}%` }}
          />
        </div>
      )}

      {/* Detail text */}
      <p className="text-sm text-foreground/90 leading-relaxed">{factor.detail}</p>

      {/* Human-readable evidence */}
      {factor.evidence && Object.keys(factor.evidence).length > 0 && (
        <div className="rounded-lg bg-muted/40 px-3 py-2">
          <EvidenceDisplay evidence={factor.evidence} />
        </div>
      )}

      {/* Legal citation */}
      {factor.legal_ref && (
        <details className="group">
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
    </div>
  );
}
```

### 4b: Create ScoreBreakdown component

- [ ] **Step 2: Create `frontend/components/ScoreBreakdown.tsx`**

```tsx
import type { FactorDetail } from "@/lib/api-client";

type Props = {
  factores: FactorDetail[];
  scoreTotal: number;
};

const CATEGORY_CONFIG = {
  sat: {
    label: "Listas SAT",
    description: "Art. 69, 69-B y 69-B Bis CFF",
    color: "bg-destructive",
    textColor: "text-destructive",
    bgColor: "bg-destructive/10",
  },
  discrepancia: {
    label: "Discrepancias",
    description: "Inconsistencias entre documentos",
    color: "bg-warning",
    textColor: "text-warning",
    bgColor: "bg-warning/10",
  },
  completitud: {
    label: "Completitud",
    description: "Documentos y campos faltantes",
    color: "bg-primary",
    textColor: "text-primary",
    bgColor: "bg-primary/10",
  },
} as const;

export function ScoreBreakdown({ factores, scoreTotal }: Props) {
  const byCategory = {
    sat: factores.filter((f) => f.category === "sat").reduce((s, f) => s + f.points, 0),
    discrepancia: factores.filter((f) => f.category === "discrepancia").reduce((s, f) => s + f.points, 0),
    completitud: factores.filter((f) => f.category === "completitud").reduce((s, f) => s + f.points, 0),
  };

  const total = byCategory.sat + byCategory.discrepancia + byCategory.completitud;

  if (total === 0) return null;

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        Desglose por categoría
      </p>
      <div className="grid grid-cols-3 gap-3">
        {(Object.entries(byCategory) as [keyof typeof CATEGORY_CONFIG, number][]).map(([cat, pts]) => {
          const cfg = CATEGORY_CONFIG[cat];
          return (
            <div key={cat} className={`rounded-lg p-3 ${cfg.bgColor} space-y-1`}>
              <p className={`text-xs font-medium ${cfg.textColor}`}>{cfg.label}</p>
              <p className={`text-2xl font-bold leading-none ${cfg.textColor}`}>{pts}</p>
              <p className="text-xs text-muted-foreground leading-tight">{cfg.description}</p>
            </div>
          );
        })}
      </div>

      {/* Stacked bar */}
      <div className="h-2 rounded-full overflow-hidden bg-muted flex">
        {total > 0 && (
          <>
            <div className="bg-destructive" style={{ width: `${(byCategory.sat / total) * 100}%` }} />
            <div className="bg-warning" style={{ width: `${(byCategory.discrepancia / total) * 100}%` }} />
            <div className="bg-primary" style={{ width: `${(byCategory.completitud / total) * 100}%` }} />
          </>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Total acumulado: <span className="font-semibold text-foreground">{scoreTotal} puntos</span>
        {scoreTotal > 100 && (
          <span className="ml-2 text-warning">(por encima de 100 — factor crítico activo)</span>
        )}
      </p>
    </div>
  );
}
```

### 4c: Create DecisionContext component

- [ ] **Step 3: Create `frontend/components/DecisionContext.tsx`**

```tsx
import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import type { Decision } from "@/lib/api-client";

const DECISION_CONFIG: Record<
  Decision,
  {
    icon: React.ReactNode;
    title: string;
    summary: string;
    implication: string;
    nextSteps: string[];
    borderClass: string;
    bgClass: string;
    iconClass: string;
  }
> = {
  safe: {
    icon: <CheckCircle2 className="size-5" />,
    title: "Perfil aprobado",
    summary: "El cliente no presenta hallazgos en listas fiscales del SAT ni discrepancias documentales significativas.",
    implication: "Puede proceder con la inscripción al Padrón de Importadores/Exportadores conforme a la Regla 1.4.14 RGCE 2026.",
    nextSteps: [
      "Archivar el expediente y emitir constancia de revisión KYB.",
      "Inscribir al cliente en el padrón si cumple los demás requisitos operativos.",
      "Programar revisión periódica (recomendado: cada 6 meses o ante cambio de situación fiscal).",
    ],
    borderClass: "border-success/40",
    bgClass: "bg-success/5",
    iconClass: "text-success",
  },
  review_required: {
    icon: <AlertTriangle className="size-5" />,
    title: "Revisión manual requerida",
    summary: "Se detectaron factores de riesgo que no bloquean automáticamente la operación pero exigen diligencia ampliada.",
    implication: "No se puede inscribir al cliente sin resolver primero los hallazgos identificados. El agente aduanal debe documentar las acciones correctivas tomadas.",
    nextSteps: [
      "Ejecutar las acciones requeridas listadas en la sección siguiente.",
      "Solicitar documentación adicional o aclaración ante el SAT según corresponda.",
      "Re-evaluar el expediente una vez resueltos los hallazgos.",
      "Documentar el proceso de diligencia en el expediente físico.",
    ],
    borderClass: "border-warning/40",
    bgClass: "bg-warning/5",
    iconClass: "text-warning",
  },
  high_risk: {
    icon: <XCircle className="size-5" />,
    title: "Alto riesgo — no operar",
    summary: "El RFC del cliente está vinculado a un bloqueo crítico (EFOS definitivo u otro hallazgo grave) que impide la operación bajo cualquier circunstancia.",
    implication: "Operar con este cliente expone a la agencia a responsabilidad solidaria por créditos fiscales inválidos y sanciones del SAT. No inscribir al padrón hasta resolver el bloqueo.",
    nextSteps: [
      "Notificar al cliente de manera formal y documentar la comunicación.",
      "Si el cliente impugna, solicitar resolución formal del SAT que acredite la desvirtuación del listado.",
      "No emitir ni aceptar CFDIs relacionados con este RFC hasta obtener resolución favorable.",
      "Consultar al área jurídica de la agencia antes de cualquier acción adicional.",
    ],
    borderClass: "border-destructive/40",
    bgClass: "bg-destructive/5",
    iconClass: "text-destructive",
  },
};

type Props = {
  decision: Decision;
  scoreTotal: number;
  hasCriticalBlock: boolean;
};

export function DecisionContext({ decision, scoreTotal, hasCriticalBlock }: Props) {
  const cfg = DECISION_CONFIG[decision];

  return (
    <div className={`rounded-xl border ${cfg.borderClass} ${cfg.bgClass} p-5 space-y-4`}>
      <div className="flex items-start gap-3">
        <span className={cfg.iconClass}>{cfg.icon}</span>
        <div className="space-y-1">
          <p className={`text-base font-semibold ${cfg.iconClass}`}>{cfg.title}</p>
          <p className="text-sm text-foreground/90 leading-relaxed">{cfg.summary}</p>
        </div>
      </div>

      {/* Score explanation */}
      <div className="rounded-lg bg-background/60 px-4 py-3 space-y-1">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          ¿Cómo se calculó este resultado?
        </p>
        <p className="text-sm text-foreground/80 leading-relaxed">
          El sistema acumuló{" "}
          <span className="font-semibold">{scoreTotal} puntos de riesgo</span> sumando los factores
          detectados. Scores por debajo de 30 son aprobados, entre 30 y 69 requieren revisión, y 70 o
          más resultan en bloqueo.{" "}
          {hasCriticalBlock && (
            <span className="text-destructive font-medium">
              Además, se activó al menos un factor de bloqueo crítico (puntaje máximo automático).
            </span>
          )}
        </p>
      </div>

      {/* Operational implication */}
      <div className="flex items-start gap-2">
        <Info className="size-4 shrink-0 mt-0.5 text-muted-foreground" />
        <p className="text-sm text-muted-foreground leading-relaxed">{cfg.implication}</p>
      </div>

      {/* Next steps */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Pasos recomendados
        </p>
        <ol className="space-y-1.5">
          {cfg.nextSteps.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
              <span className="shrink-0 w-5 h-5 rounded-full bg-muted flex items-center justify-center text-xs font-semibold text-muted-foreground mt-0.5">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
```

### 4d: Create ActionCard component

- [ ] **Step 4: Create `frontend/components/ActionCard.tsx`**

```tsx
import { ShieldAlert, AlertTriangle, FolderSearch, FileCheck2, Scale } from "lucide-react";
import type { FactorDetail } from "@/lib/api-client";

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  sat: <ShieldAlert className="size-4 text-destructive shrink-0 mt-0.5" />,
  discrepancia: <AlertTriangle className="size-4 text-warning shrink-0 mt-0.5" />,
  completitud: <FolderSearch className="size-4 text-primary shrink-0 mt-0.5" />,
  otro: <FileCheck2 className="size-4 text-muted-foreground shrink-0 mt-0.5" />,
};

const PRIORITY_LABEL: Record<string, { label: string; className: string }> = {
  sat: { label: "Prioridad alta", className: "bg-destructive/15 text-destructive" },
  discrepancia: { label: "Prioridad media", className: "bg-warning/15 text-warning" },
  completitud: { label: "Prioridad estándar", className: "bg-primary/15 text-primary" },
  otro: { label: "Informativo", className: "bg-muted text-muted-foreground" },
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

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl border border-border bg-card">
      <div className="shrink-0 w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground mt-0.5">
        {index + 1}
      </div>
      {icon}
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${priority.className}`}>
            {priority.label}
          </span>
        </div>
        <p className="text-sm font-medium leading-snug">{accion}</p>
        {relatedFactor?.legal_ref && (
          <div className="flex items-start gap-1.5">
            <Scale className="size-3 shrink-0 mt-0.5 text-muted-foreground" />
            <p className="text-xs text-muted-foreground leading-relaxed">
              {relatedFactor.legal_ref.split(" — ")[0]}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
```

### 4e: Update report page to use all new components

- [ ] **Step 5: Update `frontend/app/expedientes/[id]/reporte/page.tsx`**

Add imports at the top (after existing imports):
```tsx
import { ScoreBreakdown } from "@/components/ScoreBreakdown";
import { DecisionContext } from "@/components/DecisionContext";
import { ActionCard } from "@/components/ActionCard";
```

Remove the `ACCION_CATEGORY_ICON` constant (no longer needed).

After the `<ScoreGauge>` block and before the "Risk factors" section, add:

```tsx
{/* Score breakdown by category */}
{evaluation && factoresConRiesgo.length > 0 && (
  <div className="rounded-xl border border-border bg-card p-6 mb-6">
    <ScoreBreakdown
      factores={factoresDetail}
      scoreTotal={evaluation.score_total}
    />
  </div>
)}

{/* Decision context */}
{evaluation && (
  <div className="mb-6">
    <DecisionContext
      decision={evaluation.decision}
      scoreTotal={evaluation.score_total}
      hasCriticalBlock={factoresDetail.some((f) => f.is_critical_block)}
    />
  </div>
)}
```

Replace the existing `acciones_sugeridas` section with:
```tsx
{evaluation?.acciones_sugeridas && evaluation.acciones_sugeridas.length > 0 && (
  <section className="mb-6">
    <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
      Acciones requeridas ({evaluation.acciones_sugeridas.length})
    </h2>
    <div className="space-y-3">
      {evaluation.acciones_sugeridas.map((accion, i) => {
        const relatedFactor = factoresConRiesgo.find((f) =>
          accion.toLowerCase().includes(f.factor_code.split("_")[0])
        ) ?? factoresConRiesgo[i] ?? factoresConRiesgo[0];
        return (
          <ActionCard key={i} accion={accion} relatedFactor={relatedFactor} index={i} />
        );
      })}
    </div>
  </section>
)}
```

Also remove the old `ACCION_CATEGORY_ICON` constant from the file (it was declared at the top with emoji values).

- [ ] **Step 6: Build check**

```bash
cd frontend && pnpm build 2>&1 | tail -40
```
Expected: clean build, no TypeScript errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/FactorDetailCard.tsx frontend/components/ScoreGauge.tsx \
        frontend/components/ScoreBreakdown.tsx frontend/components/DecisionContext.tsx \
        frontend/components/ActionCard.tsx frontend/app/expedientes/[id]/reporte/page.tsx
git commit -m "feat: enrich KYB report with score breakdown, decision context, rich action cards"
```

---

## Task 5: Generate 3 synthetic demo PDFs

**Files:**
- Create: `backend/scripts/generate_demo_pdfs.py`
- Output: `backend/scripts/demo_pdfs/` (3 PDF files)

**Context:**
- Must be text-selectable (not scanned images) so Groq can extract text
- EKU9003173C9 — clean profile (Escuela Kemper Urgate SA de CV)
- COX010101AB1 — discrepancy scenario: razón social differs slightly between docs
- High-risk RFC from 69-B list (already in DB as `AAA120730823`)
- Use `reportlab` library (add via `uv add reportlab` in backend/)

- [ ] **Step 1: Install reportlab**

```bash
cd backend && uv add reportlab
```

- [ ] **Step 2: Create `backend/scripts/generate_demo_pdfs.py`**

```python
"""Generate 3 text-selectable synthetic PDFs for KYB demo scenarios."""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

OUTPUT_DIR = Path(__file__).parent / "demo_pdfs"
OUTPUT_DIR.mkdir(exist_ok=True)


def make_csf(path: Path, rfc: str, razon_social: str, domicilio: str, rep_legal: str):
    """Constancia de Situación Fiscal (simplified SAT format)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, h - 2 * cm, "CONSTANCIA DE SITUACIÓN FISCAL")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "Servicio de Administración Tributaria")
    c.line(2 * cm, h - 3.2 * cm, w - 2 * cm, h - 3.2 * cm)

    fields = [
        ("RFC:", rfc),
        ("Razón Social:", razon_social),
        ("Régimen Fiscal:", "601 - General de Ley Personas Morales"),
        ("Domicilio Fiscal:", domicilio),
        ("Representante Legal:", rep_legal),
        ("Fecha de emisión:", "2026-06-01"),
        ("Estatus en el RFC:", "ACTIVO"),
    ]
    y = h - 4.5 * cm
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(7 * cm, y, value)
        y -= 0.8 * cm

    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 2 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")
    c.save()


def make_acta(path: Path, rfc: str, razon_social: str, rep_legal: str, socios: list[str]):
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "ACTA CONSTITUTIVA")
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 2.7 * cm, "Sociedad Anónima de Capital Variable")

    c.setFont("Helvetica", 9)
    y = h - 4 * cm
    lines = [
        f"En la Ciudad de México, siendo las 10:00 horas del 1 de enero de 2015, comparecen:",
        f"Razón Social: {razon_social}",
        f"RFC: {rfc}",
        f"Representante Legal: {rep_legal}",
        "",
        "SOCIOS / ACCIONISTAS:",
    ]
    for line in lines:
        c.drawString(2 * cm, y, line)
        y -= 0.65 * cm
    for socio in socios:
        c.drawString(2.5 * cm, y, f"• {socio}")
        y -= 0.65 * cm

    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 2 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")
    c.save()


def make_comprobante_domicilio(path: Path, razon_social: str, domicilio: str, fecha: str):
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 2 * cm, "COMPROBANTE DE DOMICILIO")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 2.8 * cm, "CFE — Compañía de Luz y Fuerza del Centro")

    fields = [
        ("Nombre / Razón Social:", razon_social),
        ("Domicilio:", domicilio),
        ("Fecha de emisión:", fecha),
        ("Periodo de servicio:", "Mayo 2026"),
        ("No. de cuenta:", "00123456789"),
    ]
    y = h - 4.5 * cm
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(8 * cm, y, value)
        y -= 0.8 * cm

    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 2 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")
    c.save()


def make_manifestacion(path: Path, razon_social: str, rfc: str, rep_legal: str, declara: bool):
    c = canvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, h - 2 * cm, "MANIFESTACIÓN BAJO PROTESTA DE DECIR VERDAD")

    c.setFont("Helvetica", 9)
    y = h - 3.5 * cm
    texto = (
        f"Yo, {rep_legal}, en mi carácter de representante legal de {razon_social} "
        f"(RFC: {rfc}), manifiesto bajo protesta de decir verdad que la empresa que represento:"
    )
    # Word-wrap basic
    words = texto.split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if c.stringWidth(test, "Helvetica", 9) < (w - 4 * cm):
            line = test
        else:
            c.drawString(2 * cm, y, line)
            y -= 0.55 * cm
            line = word
    if line:
        c.drawString(2 * cm, y, line)
        y -= 0.8 * cm

    if declara:
        clausulas = [
            "1. No se encuentra en los supuestos del Art. 69-B del CFF (EFOS).",
            "2. No ha transmitido indebidamente pérdidas fiscales (Art. 69-B Bis CFF).",
            "3. No realiza operaciones de contrabando técnico (Art. 49 Bis CFF).",
            "4. Toda la información proporcionada es verídica y verificable.",
        ]
    else:
        clausulas = [
            "1. La empresa cumple con sus obligaciones fiscales.",
            "2. Toda la información proporcionada es verídica.",
        ]

    for clausula in clausulas:
        c.drawString(2 * cm, y, clausula)
        y -= 0.65 * cm

    y -= 0.5 * cm
    c.drawString(2 * cm, y, f"Firma: ________________________    Fecha: 2026-06-15")

    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(w / 2, 2 * cm, "Documento generado para fines de demostración — KYB Agencia Aduanal")
    c.save()


def generate():
    # ── Scenario 1: CLEAN — EKU9003173C9 ──────────────────────────────────────
    clean_dir = OUTPUT_DIR / "escenario_1_limpio"
    clean_dir.mkdir(exist_ok=True)
    make_csf(
        clean_dir / "csf.pdf",
        rfc="EKU9003173C9",
        razon_social="Escuela Kemper Urgate SA de CV",
        domicilio="Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
        rep_legal="Juan Pérez García",
    )
    make_acta(
        clean_dir / "acta_constitutiva.pdf",
        rfc="EKU9003173C9",
        razon_social="Escuela Kemper Urgate SA de CV",
        rep_legal="Juan Pérez García",
        socios=["Juan Pérez García (60%)", "María López Ramírez (40%)"],
    )
    make_comprobante_domicilio(
        clean_dir / "comprobante_domicilio.pdf",
        razon_social="Escuela Kemper Urgate SA de CV",
        domicilio="Av. Insurgentes Sur 123, Col. Roma Norte, CDMX, CP 06700",
        fecha="2026-06-01",
    )
    make_manifestacion(
        clean_dir / "manifestacion_protesta.pdf",
        razon_social="Escuela Kemper Urgate SA de CV",
        rfc="EKU9003173C9",
        rep_legal="Juan Pérez García",
        declara=True,
    )

    # ── Scenario 2: DISCREPANCY — COX010101AB1 ────────────────────────────────
    disc_dir = OUTPUT_DIR / "escenario_2_discrepancia"
    disc_dir.mkdir(exist_ok=True)
    make_csf(
        disc_dir / "csf.pdf",
        rfc="COX010101AB1",
        razon_social="Corporativo X SA de CV",            # canonical name
        domicilio="Avenida Insurgentes Sur Num 123, Colonia Roma",
        rep_legal="María López",
    )
    make_acta(
        disc_dir / "acta_constitutiva.pdf",
        rfc="COX010101AB1",
        razon_social="Corporativo X, S.A. de C.V.",       # slight variation → disc_razon_social
        rep_legal="Maria Lopez Hernandez",                 # full name → disc_representante match
        socios=["María López Hernandez (51%)", "Roberto Sánchez Cruz (49%)"],
    )
    make_comprobante_domicilio(
        disc_dir / "comprobante_domicilio.pdf",
        razon_social="Corporativo X SA de CV",
        domicilio="Insurgentes Sur 123, Roma",             # variation → disc_domicilio
        fecha="2026-06-01",
    )
    make_manifestacion(
        disc_dir / "manifestacion_protesta.pdf",
        razon_social="Corporativo X SA de CV",
        rfc="COX010101AB1",
        rep_legal="María López",
        declara=True,
    )

    # ── Scenario 3: HIGH RISK — AAA120730823 (69-B Definitivos) ───────────────
    risk_dir = OUTPUT_DIR / "escenario_3_alto_riesgo"
    risk_dir.mkdir(exist_ok=True)
    make_csf(
        risk_dir / "csf.pdf",
        rfc="AAA120730823",
        razon_social="Empresa en Lista Negra SA de CV",
        domicilio="Calle Reforma 456, Col. Centro, CDMX, CP 06000",
        rep_legal="Carlos Sánchez",
    )
    make_acta(
        risk_dir / "acta_constitutiva.pdf",
        rfc="AAA120730823",
        razon_social="Empresa en Lista Negra SA de CV",
        rep_legal="Carlos Sánchez",
        socios=["Carlos Sánchez (100%)"],
    )
    make_comprobante_domicilio(
        risk_dir / "comprobante_domicilio.pdf",
        razon_social="Empresa en Lista Negra SA de CV",
        domicilio="Calle Reforma 456, Col. Centro, CDMX, CP 06000",
        fecha="2026-06-01",
    )
    make_manifestacion(
        risk_dir / "manifestacion_protesta.pdf",
        razon_social="Empresa en Lista Negra SA de CV",
        rfc="AAA120730823",
        rep_legal="Carlos Sánchez",
        declara=False,   # missing 69-B/49-Bis clauses → manifestacion_incompleta
    )

    print("Demo PDFs generated:")
    for f in sorted(OUTPUT_DIR.rglob("*.pdf")):
        print(f"  {f.relative_to(OUTPUT_DIR.parent.parent)}")


if __name__ == "__main__":
    generate()
```

- [ ] **Step 3: Run the generator**

```bash
cd backend && uv run python scripts/generate_demo_pdfs.py
```
Expected output:
```
Demo PDFs generated:
  scripts/demo_pdfs/escenario_1_limpio/acta_constitutiva.pdf
  scripts/demo_pdfs/escenario_1_limpio/comprobante_domicilio.pdf
  scripts/demo_pdfs/escenario_1_limpio/csf.pdf
  scripts/demo_pdfs/escenario_1_limpio/manifestacion_protesta.pdf
  scripts/demo_pdfs/escenario_2_discrepancia/acta_constitutiva.pdf
  ...
```

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/generate_demo_pdfs.py backend/scripts/demo_pdfs/ backend/pyproject.toml backend/uv.lock
git commit -m "feat: generate 3 synthetic demo PDFs (clean, discrepancy, high-risk)"
```

---

## Self-Review

### Spec coverage
- [x] kyb-docs bucket — Task 1 (done)
- [x] Folder drag-drop bug — Task 2
- [x] Stale closure — Task 2
- [x] Failed to fetch (bucket missing) — Task 1
- [x] Emojis → SVGs — Tasks 2, 4
- [x] Raw JSON evidence — Task 4 (FactorDetailCard EvidenceDisplay)
- [x] Dashboard navigation — Task 3
- [x] Score breakdown by category — Task 4 (ScoreBreakdown)
- [x] Decision context + implications — Task 4 (DecisionContext)
- [x] Rich action cards — Task 4 (ActionCard)
- [x] StepperHeader clickable — Task 3
- [x] Audit SAT tab human-readable — Task 3
- [x] Demo PDFs — Task 5
- [x] Post-upload CTA — Task 2

### Placeholder scan
- No TBD/TODO in any step
- All code blocks are complete and self-contained

### Type consistency
- `FactorDetail` type imported from `@/lib/api-client` throughout — consistent
- `Decision` type used as imported in DecisionContext — consistent
- `expedienteId?: string` added to StepperHeader props — all callers updated in Task 3
