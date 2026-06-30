"use client";
import { use, useState } from "react";
import Link from "next/link";
import { Pencil } from "lucide-react";
import useSWR from "swr";
import { api } from "@/lib/api-client";
import type { ConsultaSat } from "@/lib/api-client";
import { useExpediente, useDocumentos } from "@/hooks/use-expediente";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SmartDropZone } from "@/components/SmartDropZone";
import { StepperHeader } from "@/components/StepperHeader";
import { ExpedienteActions } from "@/components/ExpedienteActions";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { toast } from "sonner";

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

const LIST_TYPE_LABELS: Record<string, string> = {
  art_69: "Art. 69 CFF — Incumplidos",
  art_69b: "Art. 69-B CFF — EFOS",
  art_69b_bis: "Art. 69-B Bis CFF — Pérdidas",
};

export default function ExpedienteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const { expediente, mutate: mutateExpediente } = useExpediente(id);
  const { documentos, mutate: mutateDocumentos } = useDocumentos(id);
  const { data: consultasSat = [] } = useSWR<ConsultaSat[]>(
    `consultas-sat-${id}`,
    () => api.listConsultasSat(id)
  );

  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editData, setEditData] = useState({
    razon_social: "",
    rfc: "",
    domicilio_fiscal: "",
    representante_legal: "",
  });
  const [saving, setSaving] = useState(false);

  function openEdit() {
    if (!expediente) return;
    setEditData({
      razon_social: expediente.razon_social,
      rfc: expediente.rfc,
      domicilio_fiscal: expediente.domicilio_fiscal ?? "",
      representante_legal: expediente.representante_legal ?? "",
    });
    setEditOpen(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      await api.updateExpediente(id, editData);
      toast.success("Expediente actualizado");
      await mutateExpediente();
      setEditOpen(false);
    } catch {
      toast.error("Error al actualizar");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteDocumento(docId: string) {
    setDeletingId(docId);
    try {
      await api.deleteDocumento(docId);
      toast.success("Documento eliminado");
      await mutateDocumentos();
    } catch {
      toast.error("Error al eliminar documento");
    } finally {
      setDeletingId(null);
    }
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

  const existingDocTypes = documentos.map((d) => d.doc_type);
  const totalRequired = Object.keys(DOC_TYPE_LABELS).length;
  const reviewedCount = documentos.filter((d) => d.extraction_status === "human_reviewed").length;

  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      <StepperHeader currentStep={2} expedienteId={id} />

      {/* Inline edit dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar expediente</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Razón social</label>
              <Input
                value={editData.razon_social}
                onChange={(e) => setEditData((d) => ({ ...d, razon_social: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">RFC</label>
              <Input
                value={editData.rfc}
                onChange={(e) => setEditData((d) => ({ ...d, rfc: e.target.value }))}
                className="font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Domicilio fiscal</label>
              <Input
                value={editData.domicilio_fiscal}
                onChange={(e) => setEditData((d) => ({ ...d, domicilio_fiscal: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Representante legal</label>
              <Input
                value={editData.representante_legal}
                onChange={(e) => setEditData((d) => ({ ...d, representante_legal: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancelar</DialogClose>
            <Button onClick={saveEdit} disabled={saving} className="bg-primary text-primary-foreground">
              {saving ? "Guardando…" : "Guardar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Header */}
      <div className="mb-6">
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          ← Expedientes
        </Link>
        <div className="flex items-start justify-between gap-4 mt-2">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{expediente.razon_social}</h1>
              <button
                onClick={openEdit}
                className="text-muted-foreground hover:text-foreground"
                title="Editar datos"
              >
                <Pencil className="size-4" />
              </button>
            </div>
            <p className="text-muted-foreground font-mono text-sm">{expediente.rfc}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <ExpedienteActions expediente={expediente} redirectOnDelete={true} />
            <Link
              href={`/expedientes/${id}/reporte`}
              className="inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all"
            >
              Ver reporte KYB →
            </Link>
          </div>
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
        />
      </section>

      {/* Document status grid */}
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
                  {doc && (
                    <button
                      onClick={() => {
                        if (confirm("¿Eliminar este documento? Esta acción no se puede deshacer.")) {
                          handleDeleteDocumento(doc.id);
                        }
                      }}
                      disabled={deletingId === doc.id}
                      className="text-xs text-destructive hover:underline disabled:opacity-50"
                    >
                      {deletingId === doc.id ? "Eliminando…" : "Eliminar"}
                    </button>
                  )}
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
          <TabsTrigger value="audit">Consultas SAT ({consultasSat.length})</TabsTrigger>
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
                        <td className="px-4 py-3 text-muted-foreground text-xs capitalize">
                          {doc.entry_method === "uploaded" ? "Subido" : "Manual"}
                        </td>
                        <td className="px-4 py-3">
                          <Badge className={`text-xs ${statusInfo.className}`}>{statusInfo.label}</Badge>
                        </td>
                        <td className="px-4 py-3 text-right space-x-3">
                          {(doc.extraction_status === "extracted" || doc.extraction_status === "not_applicable") && (
                            <Link href={`/expedientes/${id}/revisar?documento_id=${doc.id}`} className="text-xs text-primary hover:underline">
                              Revisar →
                            </Link>
                          )}
                          <button
                            onClick={() => {
                              if (confirm("¿Eliminar este documento? Esta acción no se puede deshacer.")) {
                                handleDeleteDocumento(doc.id);
                              }
                            }}
                            disabled={deletingId === doc.id}
                            className="text-xs text-destructive hover:underline disabled:opacity-50"
                          >
                            {deletingId === doc.id ? "Eliminando…" : "Eliminar"}
                          </button>
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
                  {consultasSat.map((c) => {
                    const found = c.found;
                    const substate = c.match_substate;
                    let badgeClass = "bg-success/15 text-success";
                    let badgeLabel = "Sin coincidencia";
                    if (found && substate === "definitivo") {
                      badgeClass = "bg-destructive text-background";
                      badgeLabel = "EFOS Definitivo";
                    } else if (found && substate === "presunto") {
                      badgeClass = "bg-destructive/15 text-destructive";
                      badgeLabel = "EFOS Presunto";
                    } else if (found) {
                      badgeClass = "bg-warning/15 text-warning";
                      badgeLabel = `Encontrado${substate ? ` — ${substate}` : ""}`;
                    }
                    return (
                      <tr key={c.id} className="border-t border-border">
                        <td className="px-3 py-2">
                          {LIST_TYPE_LABELS[c.list_type] ?? c.list_type ?? "—"}
                        </td>
                        <td className="px-3 py-2 font-mono">{c.rfc_consultado ?? "—"}</td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${badgeClass}`}>
                            {badgeLabel}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right">
                          {c.consulted_at
                            ? new Date(c.consulted_at).toLocaleString("es-MX")
                            : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </main>
  );
}
