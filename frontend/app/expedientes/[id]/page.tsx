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
