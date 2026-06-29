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
