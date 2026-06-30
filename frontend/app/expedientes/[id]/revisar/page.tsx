"use client";
import { use, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, type Documento } from "@/lib/api-client";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Plus, Trash2 } from "lucide-react";
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

type Socio = { nombre: string; rfc: string; porcentaje: string };

function parseSocios(raw: string): Socio[] {
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((s: unknown) => {
      const obj = s as Record<string, unknown>;
      return {
        nombre: String(obj.nombre ?? ""),
        rfc: String(obj.rfc ?? ""),
        porcentaje: String(obj.porcentaje ?? ""),
      };
    });
  } catch {
    return [];
  }
}

function SociosEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [socios, setSocios] = useState<Socio[]>(() => parseSocios(value));

  function update(index: number, field: keyof Socio, val: string) {
    const next = socios.map((s, i) => (i === index ? { ...s, [field]: val } : s));
    setSocios(next);
    onChange(JSON.stringify(next.map((s) => ({ ...s, porcentaje: Number(s.porcentaje) || 0 }))));
  }

  function add() {
    const next = [...socios, { nombre: "", rfc: "", porcentaje: "" }];
    setSocios(next);
    onChange(JSON.stringify(next.map((s) => ({ ...s, porcentaje: Number(s.porcentaje) || 0 }))));
  }

  function remove(index: number) {
    const next = socios.filter((_, i) => i !== index);
    setSocios(next);
    onChange(JSON.stringify(next.map((s) => ({ ...s, porcentaje: Number(s.porcentaje) || 0 }))));
  }

  return (
    <div className="space-y-3">
      {socios.map((s, i) => (
        <div key={i} className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Socio {i + 1}</span>
            <button
              type="button"
              onClick={() => remove(i)}
              className="text-muted-foreground hover:text-destructive transition-colors"
              aria-label="Eliminar socio"
            >
              <Trash2 className="size-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="col-span-2">
              <label className="text-xs text-muted-foreground block mb-0.5">Nombre</label>
              <input
                value={s.nombre}
                onChange={(e) => update(i, "nombre", e.target.value)}
                className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="Nombre completo"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-0.5">RFC</label>
              <input
                value={s.rfc}
                onChange={(e) => update(i, "rfc", e.target.value.toUpperCase())}
                className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="RFC"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-0.5">% participación</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                value={s.porcentaje}
                onChange={(e) => update(i, "porcentaje", e.target.value)}
                className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="0"
              />
            </div>
          </div>
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 transition-colors"
      >
        <Plus className="size-3.5" />
        Agregar socio
      </button>
    </div>
  );
}

function FieldDisplay({ campo, valor }: { campo: string; valor: unknown }) {
  if (campo === "socios" && Array.isArray(valor) && valor.length > 0) {
    return (
      <div className="space-y-2">
        {valor.map((s: unknown, i: number) => {
          const obj = s as Record<string, unknown>;
          return (
            <div key={i} className="text-xs rounded-lg border border-border bg-muted/30 p-2.5 space-y-0.5">
              <p className="font-medium">{String(obj.nombre ?? "—")}</p>
              <p className="font-mono text-muted-foreground">{String(obj.rfc ?? "—")}</p>
              {obj.porcentaje != null && (
                <p className="text-muted-foreground">{String(obj.porcentaje)}%</p>
              )}
            </div>
          );
        })}
      </div>
    );
  }
  if (campo === "socios") {
    return <span className="text-muted-foreground text-xs">Sin socios registrados</span>;
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
  const [remainingDocs, setRemainingDocs] = useState<{ id: string; doc_type: string }[]>([]);

  useEffect(() => {
    // Reset all state for the new document so the success screen doesn't persist
    // when the user navigates to a different documento_id on the same route.
    setSaved(false);
    setDoc(null);
    setFields({});
    setError(null);
    setRemainingDocs([]);

    if (!documento_id) {
      setLoading(false);
      return;
    }

    setLoading(true);
    api
      .getDocumento(id, documento_id)
      .then((d) => {
        setDoc(d);
        if (d?.fields) {
          const stringified: Record<string, string> = {};
          for (const [k, v] of Object.entries(d.fields)) {
            if (k === "socios" && Array.isArray(v)) {
              stringified[k] = JSON.stringify(v);
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
                if (campo === "socios") {
                  return (
                    <div key={campo}>
                      <label className="text-xs text-muted-foreground block mb-2">
                        {FIELD_LABELS[campo] ?? campo}
                      </label>
                      <SociosEditor
                        value={valor}
                        onChange={(v) => setFields({ ...fields, [campo]: v })}
                      />
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
                      rows={2}
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
