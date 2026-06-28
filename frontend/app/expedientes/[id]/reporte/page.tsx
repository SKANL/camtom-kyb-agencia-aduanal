import Link from "next/link";
import { api } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { EvaluateButton } from "./EvaluateButton";

const DECISION_BADGE: Record<string, { label: string; className: string }> = {
  safe: { label: "✓ Safe", className: "bg-success text-background text-base px-3 py-1" },
  review_required: { label: "⚠ Review required", className: "bg-warning text-background text-base px-3 py-1" },
  high_risk: { label: "✕ High risk", className: "bg-destructive text-background text-base px-3 py-1" },
};

export default async function ReportePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let expediente = null;
  let evaluation = null;
  try {
    [expediente, evaluation] = await Promise.all([
      api.getExpediente(id),
      api.getLatestEvaluation(id).catch(() => null),
    ]);
  } catch {
    // Not reachable at build time
  }

  if (!expediente) {
    return (
      <main className="min-h-screen bg-background text-foreground p-8 flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">Expediente no encontrado.</p>
          <Link href="/" className="text-primary hover:underline mt-4 block">← Volver</Link>
        </div>
      </main>
    );
  }

  const badge = expediente.decision ? DECISION_BADGE[expediente.decision] : null;

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">← Expedientes</Link>
          <h1 className="text-2xl font-bold mt-2">{expediente.razon_social}</h1>
          <p className="text-muted-foreground font-mono text-sm">{expediente.rfc}</p>
        </div>

        {/* Score card */}
        <div className="rounded-lg border border-border bg-card p-6 mb-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Decisión KYB</p>
              {badge ? (
                <Badge className={badge.className}>{badge.label}</Badge>
              ) : (
                <span className="text-muted-foreground">Sin evaluar</span>
              )}
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground mb-1">Score de riesgo</p>
              <p className="text-5xl font-bold text-primary">
                {expediente.score_total ?? "—"}
                {expediente.score_total !== null && <span className="text-lg text-muted-foreground ml-1">pts</span>}
              </p>
            </div>
          </div>
        </div>

        {/* Acciones sugeridas */}
        {evaluation?.acciones_sugeridas && evaluation.acciones_sugeridas.length > 0 && (
          <div className="rounded-lg border border-border bg-card p-6 mb-6">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
              Acciones sugeridas
            </h2>
            <ul className="space-y-2">
              {evaluation.acciones_sugeridas.map((accion: string) => (
                <li key={accion} className="flex items-start gap-2 text-sm">
                  <span className="text-warning mt-0.5">›</span>
                  <span>{accion}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Expediente details */}
        <div className="rounded-lg border border-border bg-card p-6 mb-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Datos del expediente</h2>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div><dt className="text-muted-foreground">Estado</dt><dd className="capitalize">{expediente.status}</dd></div>
            {expediente.domicilio_fiscal && <div><dt className="text-muted-foreground">Domicilio fiscal</dt><dd>{expediente.domicilio_fiscal}</dd></div>}
            {expediente.representante_legal && <div><dt className="text-muted-foreground">Representante legal</dt><dd>{expediente.representante_legal}</dd></div>}
            {evaluation?.evaluated_at && <div><dt className="text-muted-foreground">Última evaluación</dt><dd>{new Date(evaluation.evaluated_at).toLocaleString("es-MX")}</dd></div>}
          </dl>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <EvaluateButton expedienteId={id} />
          <Link
            href={`/expedientes/${id}/revisar`}
            className="inline-flex items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-surface-elevated transition-all"
          >
            Revisar documentos
          </Link>
        </div>
      </div>
    </main>
  );
}
