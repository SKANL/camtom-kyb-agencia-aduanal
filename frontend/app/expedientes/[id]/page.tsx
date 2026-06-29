import Link from "next/link";
import { api } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DocumentUploader } from "@/components/DocumentUploader";

const DOC_TYPE_LABELS: Record<string, string> = {
  csf: "Const. Situación Fiscal",
  acta_constitutiva: "Acta Constitutiva",
  comprobante_domicilio: "Comprobante Domicilio",
  identificacion_rep_legal: "ID Rep. Legal",
  poder_notarial: "Poder Notarial",
  encargo_conferido: "Encargo Conferido",
  manifestacion_protesta: "Manifestación Protesta",
};

const EXTRACTION_STATUS_BADGE: Record<
  string,
  { label: string; className: string }
> = {
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
        <Link href="/" className="text-primary hover:underline">
          ← Volver
        </Link>
      </main>
    );
  }

  const docsByType = Object.fromEntries(
    documentos.map((d) => [d.doc_type, d])
  );

  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Expedientes
        </Link>
        <h1 className="text-2xl font-bold mt-2">{expediente.razon_social}</h1>
        <p className="text-muted-foreground font-mono text-sm">{expediente.rfc}</p>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 mb-8">
        <Link
          href={`/expedientes/${id}/reporte`}
          className="inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all"
        >
          Ver reporte KYB
        </Link>
        <Link
          href={`/expedientes/${id}/revisar`}
          className="inline-flex items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted transition-all"
        >
          Revisar documentos
        </Link>
      </div>

      {/* Document grid */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
          Documentos requeridos ({documentos.length}/{Object.keys(DOC_TYPE_LABELS).length})
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(DOC_TYPE_LABELS).map(([docType, label]) => {
            const doc = docsByType[docType];
            const statusInfo = doc
              ? EXTRACTION_STATUS_BADGE[doc.extraction_status] ??
                EXTRACTION_STATUS_BADGE.pending
              : null;
            const canReview =
              doc &&
              (doc.extraction_status === "extracted" ||
                doc.extraction_status === "not_applicable");

            return (
              <div
                key={docType}
                className="rounded-xl border border-border bg-card p-4 space-y-3"
              >
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
                  <p className="text-xs text-success">Revisión completada</p>
                ) : (
                  <DocumentUploader
                    expedienteId={id}
                    docType={docType}
                  />
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Tabs: docs list + audit */}
      <Tabs defaultValue="audit">
        <TabsList>
          <TabsTrigger value="documentos">
            Documentos ({documentos.length})
          </TabsTrigger>
          <TabsTrigger value="audit">
            Audit log SAT ({consultasSat.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="documentos" className="mt-4">
          {documentos.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Sin documentos cargados.
            </p>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-card">
                  <tr>
                    <th className="text-left px-4 py-3 text-muted-foreground font-medium">
                      Tipo
                    </th>
                    <th className="text-left px-4 py-3 text-muted-foreground font-medium">
                      Método
                    </th>
                    <th className="text-left px-4 py-3 text-muted-foreground font-medium">
                      Estado extracción
                    </th>
                    <th className="text-right px-4 py-3 text-muted-foreground font-medium">
                      Acción
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {documentos.map((doc) => {
                    const statusInfo =
                      EXTRACTION_STATUS_BADGE[doc.extraction_status] ??
                      EXTRACTION_STATUS_BADGE.pending;
                    return (
                      <tr key={doc.id} className="border-t border-border">
                        <td className="px-4 py-3 font-mono text-xs">
                          {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
                        </td>
                        <td className="px-4 py-3 capitalize text-muted-foreground text-xs">
                          {doc.entry_method}
                        </td>
                        <td className="px-4 py-3">
                          <Badge className={`text-xs ${statusInfo.className}`}>
                            {statusInfo.label}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {(doc.extraction_status === "extracted" ||
                            doc.extraction_status === "not_applicable") && (
                            <Link
                              href={`/expedientes/${id}/revisar?documento_id=${doc.id}`}
                              className="text-xs text-primary hover:underline"
                            >
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
            Consultas realizadas contra listas fiscales del SAT (Art. 69, 69-B,
            69-B Bis)
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
                    <th className="text-left px-3 py-2 text-muted-foreground">
                      Fuente
                    </th>
                    <th className="text-left px-3 py-2 text-muted-foreground">
                      RFC consultado
                    </th>
                    <th className="text-left px-3 py-2 text-muted-foreground">
                      Resultado
                    </th>
                    <th className="text-right px-3 py-2 text-muted-foreground">
                      Fecha
                    </th>
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
                      <td className="px-3 py-2 font-mono">
                        {c.list_type ?? "—"}
                      </td>
                      <td className="px-3 py-2 font-mono">{c.rfc ?? "—"}</td>
                      <td className="px-3 py-2">{c.resultado ?? "—"}</td>
                      <td className="px-3 py-2 text-right">
                        {c.created_at
                          ? new Date(c.created_at).toLocaleString("es-MX")
                          : "—"}
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
