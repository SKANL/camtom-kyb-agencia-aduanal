"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const PIPELINE_PASOS = [
  "Subiendo archivo a Storage",
  "Extrayendo texto del PDF",
  "Clasificando campos con IA",
  "Almacenando resultado",
] as const;

type Estado = "idle" | "uploading" | "extracting" | "done" | "error";
type Props = { expedienteId: string; docType: string; onDone?: () => void };

export function DocumentUploader({ expedienteId, docType, onDone }: Props) {
  const router = useRouter();
  const [modo, setModo] = useState<"archivo" | "manual">("archivo");
  const [estado, setEstado] = useState<Estado>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [pasoActual, setPasoActual] = useState(0);

  async function subirArchivo(file: File) {
    setEstado("uploading");
    setErrorMsg(null);
    setPasoActual(0);
    try {
      const { documento_id, signed_url } = await api.crearDocumento(
        expedienteId,
        docType,
        "uploaded"
      );
      setDocId(documento_id);
      if (signed_url) {
        await fetch(signed_url, { method: "PUT", body: file });
      }
      setPasoActual(1);
      setEstado("extracting");
      setPasoActual(2);
      await api.extractDocumento(documento_id);
      setPasoActual(3);
      setEstado("done");
      onDone?.();
      router.refresh();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Error al procesar");
      setEstado("error");
    }
  }

  async function capturarManual() {
    setErrorMsg(null);
    try {
      const { documento_id } = await api.crearDocumento(
        expedienteId,
        docType,
        "manual"
      );
      window.location.href = `/expedientes/${expedienteId}/revisar?documento_id=${documento_id}`;
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Error al crear documento");
    }
  }

  if (estado === "done" && docId) {
    return (
      <div className="space-y-3">
        <p className="text-success text-sm flex items-center gap-2">
          <span>✓</span>
          <span>Extracción completada</span>
        </p>
        <Button
          size="sm"
          className="bg-primary text-primary-foreground"
          onClick={() =>
            (window.location.href = `/expedientes/${expedienteId}/revisar?documento_id=${docId}`)
          }
        >
          Revisar campos extraídos →
        </Button>
      </div>
    );
  }

  if (estado === "uploading" || estado === "extracting") {
    return (
      <ul className="space-y-1.5 text-sm">
        {PIPELINE_PASOS.map((paso, i) => {
          const done = i < pasoActual;
          const current = i === pasoActual;
          return (
            <li
              key={paso}
              className={
                done
                  ? "text-success flex items-center gap-2"
                  : current
                  ? "text-primary flex items-center gap-2 animate-pulse"
                  : "text-muted-foreground flex items-center gap-2"
              }
            >
              <span className="w-4 text-center shrink-0">
                {done ? "✓" : current ? "›" : "·"}
              </span>
              <span>{paso}{current ? "…" : ""}</span>
            </li>
          );
        })}
      </ul>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Button
          type="button"
          variant={modo === "archivo" ? "default" : "outline"}
          size="sm"
          onClick={() => setModo("archivo")}
          className={modo === "archivo" ? "bg-primary text-primary-foreground" : ""}
        >
          Subir PDF
        </Button>
        <Button
          type="button"
          variant={modo === "manual" ? "default" : "outline"}
          size="sm"
          onClick={() => setModo("manual")}
          className={modo === "manual" ? "bg-primary text-primary-foreground" : ""}
        >
          Captura manual
        </Button>
      </div>

      {modo === "archivo" ? (
        <Input
          type="file"
          accept="application/pdf"
          onChange={(e) => e.target.files?.[0] && subirArchivo(e.target.files[0])}
          className="cursor-pointer text-xs"
        />
      ) : (
        <Button
          type="button"
          size="sm"
          onClick={capturarManual}
          className="bg-primary text-primary-foreground"
        >
          Abrir formulario manual
        </Button>
      )}

      {estado === "error" && (
        <p className="text-destructive text-xs">{errorMsg ?? "Error desconocido"}</p>
      )}
    </div>
  );
}
