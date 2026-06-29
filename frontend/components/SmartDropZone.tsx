"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FolderOpen, CheckCircle2, XCircle, Loader2, AlertTriangle, X, ChevronRight, FileText,
} from "lucide-react";
import { api, DuplicateDocumentoError } from "@/lib/api-client";
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
  status: "classifying" | "classified" | "uploading" | "done" | "error";
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
    router.refresh();
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
    if (f.status === "classifying" || f.status === "uploading")
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
                    : f.status === "uploading" ? "Subiendo y extrayendo con IA..."
                    : f.status === "done" ? (f.errorMsg ?? "Procesado")
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
