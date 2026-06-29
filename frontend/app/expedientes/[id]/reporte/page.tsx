import Link from "next/link";
import { api } from "@/lib/api-client";
import { ScoreGauge } from "@/components/ScoreGauge";
import { FactorDetailCard } from "@/components/FactorDetailCard";
import { StepperHeader } from "@/components/StepperHeader";
import { EvaluateButton } from "./EvaluateButton";

const ACCION_CATEGORY_ICON: Record<string, string> = {
  sat: "🚫",
  discrepancia: "⚠️",
  completitud: "📄",
  otro: "›",
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
    // Build time
  }

  if (!expediente) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8 flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <p className="text-muted-foreground">Expediente no encontrado.</p>
          <Link href="/" className="text-primary hover:underline mt-4 block">← Volver</Link>
        </div>
      </main>
    );
  }

  const factoresDetail = evaluation?.factores_detail ?? [];
  const factoresConRiesgo = factoresDetail
    .filter((f) => f.points > 0)
    .sort((a, b) => b.points - a.points);
  const factoresSinRiesgo = factoresDetail.filter((f) => f.points === 0);
  const maxPoints = factoresConRiesgo.length
    ? Math.max(...factoresConRiesgo.map((f) => f.points))
    : 100;

  return (
    <main className="max-w-3xl mx-auto px-6 py-8">
      <StepperHeader currentStep={4} />

      {/* Breadcrumb */}
      <div className="mb-6">
        <Link href={`/expedientes/${id}`} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          ← {expediente.razon_social}
        </Link>
        <h1 className="text-2xl font-bold mt-2">Reporte KYB</h1>
        <p className="text-muted-foreground text-sm mt-1 font-mono">{expediente.rfc}</p>
      </div>

      {/* Score hero */}
      <div className="rounded-xl border border-border bg-card p-6 mb-6">
        {evaluation ? (
          <ScoreGauge score={evaluation.score_total} decision={evaluation.decision} />
        ) : (
          <div className="text-center py-4 space-y-3">
            <p className="text-muted-foreground text-sm">
              Aún no hay evaluación. Cargá los documentos y ejecutá la evaluación KYB.
            </p>
            <EvaluateButton expedienteId={id} />
          </div>
        )}
      </div>

      {/* Risk factors */}
      {factoresConRiesgo.length > 0 && (
        <section className="mb-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Factores de riesgo detectados ({factoresConRiesgo.length})
          </h2>
          <div className="space-y-3">
            {factoresConRiesgo.map((f) => (
              <FactorDetailCard key={f.factor_code} factor={f} maxPoints={maxPoints} />
            ))}
          </div>
        </section>
      )}

      {/* Acciones sugeridas */}
      {evaluation?.acciones_sugeridas && evaluation.acciones_sugeridas.length > 0 && (
        <section className="mb-6">
          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
              Acciones requeridas ({evaluation.acciones_sugeridas.length})
            </h2>
            <ul className="space-y-4">
              {evaluation.acciones_sugeridas.map((accion, i) => {
                const relatedFactor = factoresConRiesgo.find((f) =>
                  accion.toLowerCase().includes(f.factor_code.split("_")[0])
                );
                const icon = relatedFactor
                  ? ACCION_CATEGORY_ICON[relatedFactor.category]
                  : "›";
                return (
                  <li key={i} className="flex items-start gap-3">
                    <span className="shrink-0 mt-0.5 text-base">{icon}</span>
                    <div className="space-y-1">
                      <p className="text-sm">{accion}</p>
                      {relatedFactor?.legal_ref && (
                        <p className="text-xs text-muted-foreground">
                          § {relatedFactor.legal_ref.split("—")[0].trim()}
                        </p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>
      )}

      {/* Factors with 0 points (collapsed) */}
      {factoresSinRiesgo.length > 0 && (
        <section className="mb-6">
          <details>
            <summary className="text-xs text-muted-foreground uppercase tracking-wide cursor-pointer hover:text-foreground transition-colors mb-2 select-none">
              Factores verificados sin impacto en score ({factoresSinRiesgo.length})
            </summary>
            <div className="mt-3 space-y-3">
              {factoresSinRiesgo.map((f) => (
                <FactorDetailCard key={f.factor_code} factor={f} maxPoints={maxPoints} />
              ))}
            </div>
          </details>
        </section>
      )}

      {/* Expediente metadata */}
      <div className="rounded-xl border border-border bg-card p-6 mb-6">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          Datos del expediente
        </h2>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-muted-foreground text-xs">RFC</dt>
            <dd className="font-mono">{expediente.rfc}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Estado</dt>
            <dd className="capitalize">{expediente.status}</dd>
          </div>
          {expediente.domicilio_fiscal && (
            <div className="col-span-2">
              <dt className="text-muted-foreground text-xs">Domicilio fiscal</dt>
              <dd>{expediente.domicilio_fiscal}</dd>
            </div>
          )}
          {expediente.representante_legal && (
            <div className="col-span-2">
              <dt className="text-muted-foreground text-xs">Representante legal</dt>
              <dd>{expediente.representante_legal}</dd>
            </div>
          )}
          {evaluation?.evaluated_at && (
            <div className="col-span-2">
              <dt className="text-muted-foreground text-xs">Última evaluación</dt>
              <dd>{new Date(evaluation.evaluated_at).toLocaleString("es-MX")}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Actions */}
      <div className="flex gap-3 flex-wrap">
        <EvaluateButton expedienteId={id} />
        <Link
          href={`/expedientes/${id}`}
          className="inline-flex items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted transition-all"
        >
          Ver documentos
        </Link>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted transition-all"
        >
          ← Dashboard
        </Link>
      </div>
    </main>
  );
}
