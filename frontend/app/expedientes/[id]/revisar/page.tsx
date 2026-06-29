"use client";
import { use, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, type Documento } from "@/lib/api-client";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StepperHeader } from "@/components/StepperHeader";

const FIELD_LABELS: Record<string, string> = {
  rfc: "RFC",
  razon_social: "Razón social",
  domicilio_fiscal: "Domicilio fiscal",
  fecha_emision: "Fecha de emisión",
  regimen_fiscal: "Régimen fiscal",
  socios: "Socios / Accionistas",
  domicilio: "Domicilio",
  fecha_vencimiento: "Fecha de vencimiento",
  nombre_completo: "Nombre completo",
  nombre_representante: "Nombre del representante",
  alcance: "Alcance",
  rfc_agente_aduanal: "RFC agente aduanal",
  fecha_vigencia: "Fecha de vigencia",
  declara_no_69b_49bis: "Declara no estar en Art. 69-B / 49 Bis",
};

function FieldDisplay({ campo, valor }: { campo: string; valor: unknown }) {
  if (campo === "socios" && Array.isArray(valor)) {
    return (
      <div className="text-xs text-muted-foreground bg-muted/50 rounded p-2 font-mono whitespace-pre-wrap">
        {JSON.stringify(valor, null, 2)}
      </div>
    );
  }
  if (typeof valor === "boolean") {
    return (
      <Badge className={valor ? "bg-success text-background" : "bg-destructive text-background"}>
        {valor ? "Sí" : "No"}
      </Badge>
    );
  }
  return <span className="text-sm">{valor != null ? String(valor) : "—"}</span>;
}

export default function RevisarPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ documento_id?: string }>;
}) {
  const { id } = use(params);
  const { documento_id } = use(searchParams);
  const router = useRouter();

  const [doc, setDoc] = useState<Documento | null>(null);
  const [loading, setLoading] = useState(true);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documento_id) {
      setLoading(false);
      return;
    }
    api
      .getDocumento(id, documento_id)
      .then((d) => {
        setDoc(d);
        if (d?.fields) {
          const stringified: Record<string, string> = {};
          for (const [k, v] of Object.entries(d.fields)) {
            if (k === "socios" && Array.isArray(v)) {
              stringified[k] = JSON.stringify(v, null, 2);
            } else if (typeof v === "boolean") {
              stringified[k] = String(v);
            } else {
              stringified[k] = v != null ? String(v) : "";
            }
          }
          setFields(stringified);
        }
      })
      .catch(() => setError("No se pudo cargar el documento"))
      .finally(() => setLoading(false));
  }, [id, documento_id]);

  async function confirmar() {
    if (!documento_id) return;
    setSaving(true);
    setError(null);
    try {
      const parsed: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(fields)) {
        if (k === "declara_no_69b_49bis") {
          parsed[k] = v === "true";
        } else if (k === "socios") {
          try {
            parsed[k] = JSON.parse(v);
          } catch {
            parsed[k] = v;
          }
        } else {
          parsed[k] = v || null;
        }
      }
      await api.reviewDocumento(documento_id, parsed);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  if (saved) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-8 flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <p className="text-success text-2xl">✓ Revisión guardada</p>
          <p className="text-muted-foreground text-sm">
            Los campos fueron confirmados con revisión humana.
          </p>
          <div className="flex gap-3 justify-center">
            <Button
              className="bg-primary text-primary-foreground"
              onClick={() => router.push(`/expedientes/${id}/reporte`)}
            >
              Ver reporte KYB
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push(`/expedientes/${id}`)}
            >
              Volver al expediente
            </Button>
          </div>
        </div>
      </main>
    );
  }

  if (!documento_id) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-8">
        <Link
          href={`/expedientes/${id}`}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Volver al expediente
        </Link>
        <p className="text-muted-foreground mt-8 text-center">
          Seleccioná un documento desde el expediente para revisar.
        </p>
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      <StepperHeader currentStep={3} expedienteId={id} />
      <div className="mb-6">
        <Link
          href={`/expedientes/${id}`}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Expediente
        </Link>
        <h1 className="text-2xl font-bold mt-2">Revisión humana de extracción</h1>
        {doc && (
          <p className="text-muted-foreground text-sm mt-1">
            {FIELD_LABELS[doc.doc_type] ?? doc.doc_type} ·{" "}
            <span className="font-mono text-xs">{documento_id}</span>
          </p>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-6">
          {[0, 1].map((i) => (
            <div key={i} className="h-64 rounded-xl bg-card animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: extracted data (read-only reference) */}
          <div className="rounded-xl border border-border bg-card p-5">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-4">
              Datos extraídos por IA
            </p>
            {doc?.fields && Object.keys(doc.fields).length > 0 ? (
              <dl className="space-y-3">
                {Object.entries(doc.fields).map(([campo, valor]) => (
                  <div key={campo}>
                    <dt className="text-xs text-muted-foreground mb-0.5">
                      {FIELD_LABELS[campo] ?? campo}
                    </dt>
                    <dd>
                      <FieldDisplay campo={campo} valor={valor} />
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-muted-foreground text-sm">
                Sin datos extraídos — documento cargado manualmente.
              </p>
            )}
          </div>

          {/* Right: editable fields */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Confirmar o corregir
            </p>

            {Object.keys(fields).length === 0 ? (
              <p className="text-muted-foreground text-sm">
                Sin campos para revisar.
              </p>
            ) : (
              Object.entries(fields).map(([campo, valor]) => {
                if (campo === "declara_no_69b_49bis") {
                  return (
                    <div key={campo} className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        id={campo}
                        checked={valor === "true"}
                        onChange={(e) =>
                          setFields({ ...fields, [campo]: String(e.target.checked) })
                        }
                        className="w-4 h-4 accent-primary"
                      />
                      <label htmlFor={campo} className="text-sm">
                        {FIELD_LABELS[campo] ?? campo}
                      </label>
                    </div>
                  );
                }
                return (
                  <div key={campo}>
                    <label className="text-xs text-muted-foreground block mb-1">
                      {FIELD_LABELS[campo] ?? campo}
                    </label>
                    <Textarea
                      value={valor}
                      onChange={(e) =>
                        setFields({ ...fields, [campo]: e.target.value })
                      }
                      rows={campo === "socios" ? 4 : 2}
                      className="text-sm font-mono resize-none"
                    />
                  </div>
                );
              })
            )}

            {error && <p className="text-destructive text-xs">{error}</p>}

            <Button
              onClick={confirmar}
              disabled={saving || !documento_id}
              className="w-full bg-primary text-primary-foreground"
            >
              {saving ? "Guardando…" : "Confirmar revisión"}
            </Button>
          </div>
        </div>
      )}
    </main>
  );
}
