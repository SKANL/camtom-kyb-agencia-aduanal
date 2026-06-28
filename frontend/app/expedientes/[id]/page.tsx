import Link from "next/link";
import { api } from "@/lib/api-client";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default async function ExpedienteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let expediente = null;
  let documentos: unknown[] = [];
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
      <main className="min-h-screen bg-background text-foreground p-8">
        <p className="text-muted-foreground">Expediente no encontrado.</p>
        <Link href="/" className="text-primary hover:underline">← Volver</Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">← Expedientes</Link>
          <h1 className="text-2xl font-bold mt-2">{expediente.razon_social}</h1>
          <p className="text-muted-foreground font-mono text-sm">{expediente.rfc}</p>
        </div>

        <div className="flex gap-3 mb-6">
          <Link
            href={`/expedientes/${id}/reporte`}
            className="inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all"
          >
            Ver reporte
          </Link>
          <Link
            href={`/expedientes/${id}/revisar`}
            className="inline-flex items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-surface-elevated transition-all"
          >
            Revisar documentos
          </Link>
        </div>

        <Tabs defaultValue="documentos">
          <TabsList>
            <TabsTrigger value="documentos">Documentos ({documentos.length})</TabsTrigger>
            <TabsTrigger value="audit">Audit log SAT ({consultasSat.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="documentos" className="mt-4">
            {documentos.length === 0 ? (
              <p className="text-muted-foreground text-sm py-8 text-center">Sin documentos cargados.</p>
            ) : (
              <div className="rounded-lg border border-border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-card">
                    <tr>
                      <th className="text-left px-4 py-3 text-muted-foreground">Tipo</th>
                      <th className="text-left px-4 py-3 text-muted-foreground">Método</th>
                      <th className="text-left px-4 py-3 text-muted-foreground">Estado extracción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(documentos as Array<{ id: string; doc_type: string; entry_method: string; extraction_status: string }>).map((doc) => (
                      <tr key={doc.id} className="border-t border-border">
                        <td className="px-4 py-3 font-mono text-xs">{doc.doc_type}</td>
                        <td className="px-4 py-3 capitalize">{doc.entry_method}</td>
                        <td className="px-4 py-3">{doc.extraction_status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>

          <TabsContent value="audit" className="mt-4">
            <p className="text-xs text-muted-foreground mb-3">Consultas realizadas contra listas fiscales del SAT para este expediente</p>
            {consultasSat.length === 0 ? (
              <p className="text-muted-foreground text-sm py-8 text-center">Sin consultas registradas. Ejecutá una evaluación primero.</p>
            ) : (
              <div className="rounded-lg border border-border overflow-hidden">
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
                    {(consultasSat as Array<{ id: string; list_type?: string; rfc?: string; resultado?: string; created_at?: string }>).map((c) => (
                      <tr key={c.id} className="border-t border-border">
                        <td className="px-3 py-2 font-mono">{c.list_type ?? "—"}</td>
                        <td className="px-3 py-2 font-mono">{c.rfc ?? "—"}</td>
                        <td className="px-3 py-2">{c.resultado ?? "—"}</td>
                        <td className="px-3 py-2 text-right">{c.created_at ? new Date(c.created_at).toLocaleString("es-MX") : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
