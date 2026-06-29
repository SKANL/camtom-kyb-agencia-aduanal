"use client";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ExpedienteActions } from "@/components/ExpedienteActions";
import { useExpedientes } from "@/hooks/use-expedientes";
import type { Expediente, Decision } from "@/lib/api-client";

const DECISION_BADGE: Record<Decision, { label: string; className: string }> = {
  safe: { label: "Aprobado", className: "bg-success/15 text-success border-success/20" },
  review_required: { label: "Revisión requerida", className: "bg-warning/15 text-warning border-warning/20" },
  high_risk: { label: "Alto riesgo", className: "bg-destructive/15 text-destructive border-destructive/20" },
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  completed: "Completado",
  needs_update: "Actualización requerida",
  in_progress: "En progreso",
};

export function ExpedientesList({ initialExpedientes }: { initialExpedientes: Expediente[] }) {
  const { data: expedientes = initialExpedientes, isLoading } = useExpedientes(initialExpedientes);

  const safe = expedientes.filter((e) => e.decision === "safe").length;
  const flagged = expedientes.filter(
    (e) => e.decision === "review_required" || e.decision === "high_risk"
  ).length;
  const pending = expedientes.filter((e) => !e.decision).length;

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Total expedientes</p>
          <p className="text-3xl font-bold">{expedientes.length}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Aprobados</p>
          <p className="text-3xl font-bold text-success">{safe}</p>
          <p className="text-xs text-muted-foreground mt-1">safe ✓</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Requieren atención</p>
          <p className="text-3xl font-bold text-warning">{flagged + pending}</p>
          {pending > 0 && <p className="text-xs text-muted-foreground mt-1">{pending} sin evaluar</p>}
        </div>
      </div>

      {isLoading && expedientes.length === 0 ? (
        <div className="grid gap-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-14 rounded-xl bg-card animate-pulse" />
          ))}
        </div>
      ) : expedientes.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <p className="text-lg font-medium mb-2">Sin expedientes registrados</p>
          <p className="text-sm">Crea el primero para comenzar el proceso KYB.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-card">
              <tr>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Cliente</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">RFC</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Estado</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Decisión</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">Score</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {expedientes.map((e) => {
                const badge = e.decision ? DECISION_BADGE[e.decision] : null;
                const statusLabel = STATUS_LABEL[e.status] ?? e.status;
                return (
                  <tr
                    key={e.id}
                    className="border-t border-border hover:bg-card/60 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium">
                      <Link
                        href={e.decision ? `/expedientes/${e.id}/reporte` : `/expedientes/${e.id}`}
                        className="hover:text-primary transition-colors"
                      >
                        {e.razon_social}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-muted-foreground text-xs">{e.rfc}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{statusLabel}</td>
                    <td className="px-4 py-3">
                      {badge ? (
                        <Badge className={badge.className}>{badge.label}</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">Sin evaluar</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm">
                      <div className="flex items-center justify-end gap-3">
                        {e.score_total !== null ? (
                          <span className="text-primary font-bold">{e.score_total} pts</span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                        <Link
                          href={e.decision ? `/expedientes/${e.id}/reporte` : `/expedientes/${e.id}`}
                          className="text-muted-foreground hover:text-primary transition-colors"
                          title={e.decision ? "Ver reporte" : "Cargar documentos"}
                        >
                          <ChevronRight className="size-4" />
                        </Link>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ExpedienteActions expediente={e} redirectOnDelete={false} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
