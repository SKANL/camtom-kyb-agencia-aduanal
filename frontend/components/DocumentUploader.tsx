"use client";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = { expedienteId: string; docType: string };
type Estado = "idle" | "uploading" | "extracting" | "done" | "error";

const ESTADO_LABEL: Record<Estado, string> = {
  idle: "Listo",
  uploading: "Subiendo archivo…",
  extracting: "Extrayendo datos con IA…",
  done: "✓ Completado",
  error: "Error",
};

export function DocumentUploader({ expedienteId, docType }: Props) {
  const [modo, setModo] = useState<"archivo" | "manual">("archivo");
  const [estado, setEstado] = useState<Estado>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function subirArchivo(file: File) {
    setEstado("uploading");
    setErrorMsg(null);
    try {
      const { documento_id, signed_url } = await api.crearDocumento(expedienteId, docType, "uploaded");
      if (signed_url) {
        await fetch(signed_url, { method: "PUT", body: file });
      }
      setEstado("extracting");
      await api.extractDocumento(documento_id);
      setEstado("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Error al procesar");
      setEstado("error");
    }
  }

  async function capturarManual() {
    try {
      const { documento_id } = await api.crearDocumento(expedienteId, docType, "manual");
      window.location.href = `/expedientes/${expedienteId}/revisar?documento_id=${documento_id}`;
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Error al crear documento");
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex gap-2">
        <Button
          type="button"
          variant={modo === "archivo" ? "default" : "outline"}
          onClick={() => setModo("archivo")}
          className={modo === "archivo" ? "bg-primary text-primary-foreground" : ""}
          size="sm"
        >
          Subir archivo
        </Button>
        <Button
          type="button"
          variant={modo === "manual" ? "default" : "outline"}
          onClick={() => setModo("manual")}
          className={modo === "manual" ? "bg-primary text-primary-foreground" : ""}
          size="sm"
        >
          Captura manual
        </Button>
      </div>

      {modo === "archivo" ? (
        <Input
          type="file"
          accept="application/pdf"
          disabled={estado === "uploading" || estado === "extracting"}
          onChange={(e) => e.target.files?.[0] && subirArchivo(e.target.files[0])}
          className="cursor-pointer"
        />
      ) : (
        <Button
          type="button"
          onClick={capturarManual}
          className="bg-primary text-primary-foreground"
        >
          Crear registro manual
        </Button>
      )}

      <p className={`text-xs ${estado === "error" ? "text-destructive" : "text-muted-foreground"}`}>
        {errorMsg ?? ESTADO_LABEL[estado]}
      </p>
    </div>
  );
}
