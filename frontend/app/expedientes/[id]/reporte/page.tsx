import Link from "next/link";
import { api } from "@/lib/api-client";
import { ScoreGauge } from "@/components/ScoreGauge";
import { FactorDetailCard } from "@/components/FactorDetailCard";
import { StepperHeader } from "@/components/StepperHeader";
import { ScoreBreakdown } from "@/components/ScoreBreakdown";
import { DecisionContext } from "@/components/DecisionContext";
import { ActionCard } from "@/components/ActionCard";
import { EvaluateButton } from "./EvaluateButton";

const FACTOR_LABELS: Record<string, string> = {
  sat_69b_definitivo: "RFC en EFOS definitivos (Art. 69-B)",
  sat_69b_presunto: "RFC en EFOS presuntos (Art. 69-B)",
  sat_69b_bis: "RFC en transmisión pérdidas (Art. 69-B Bis)",
  sat_69_incumplido: "RFC incumplido (Art. 69)",
  rfc_formato_invalido: "RFC con formato inválido",
  art_49bis_no_verificable: "Art. 49 Bis sin lista pública",
  disc_rfc: "Discrepancia de RFC entre documentos",
  disc_razon_social: "Discrepancia de razón social",
  disc_domicilio: "Discrepancia de domicilio",
  disc_representante: "Discrepancia de representante legal",
  disc_fechas: "Inconsistencia de fechas",
  doc_missing: "Documento faltante",
  doc_data_incomplete: "Campos incompletos en documento",
  doc_expired: "Documento vencido",
  csf_stale: "CSF de mes anterior",
  manifestacion_incompleta: "Manifestación bajo Protesta incompleta",
  socios_incompletos: "Socios/accionistas sin registrar",
  rep_legal_incompleto: "Nombre de rep. legal faltante",
};

function FactorRow({
  code,
  points,
  maxPoints,
}: {
  code: string;
  points: number;
  maxPoints: number;
}) {
  const pct = maxPoints > 0 ? Math.min((points / maxPoints) * 100, 100) : 0;
  const barColor =
    points === 0
      ? "bg-success"
      : points >= 50
      ? "bg-destructive"
      : "bg-warning";

  return (
    <div className="flex items-center gap-3 py-2">
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate">
          {FACTOR_LABELS[code] ?? code}
        </p>
      </div>
      <div className="w-32 shrink-0">
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <div className="w-14 text-right">
        <span
          className={`text-sm font-mono font-bold ${
            points === 0
              ? "text-success"
              : points >= 50
              ? "text-destructive"
              : "text-warning"
          }`}
        >
          {points === 0 ? "—" : `+${points}`}
        </span>
      </div>
    </div>
  );
}

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
          <Link href="/" className="text-primary hover:underline mt-4 block">
            ← Volver
          </Link>
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
      <StepperHeader currentStep={4} expedienteId={id} />

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

      {/* Score breakdown by category */}
      {evaluation && factoresConRiesgo.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6 mb-6">
          <ScoreBreakdown
            factores={factoresDetail}
            scoreTotal={evaluation.score_total}
          />
        </div>
      )}

      {/* Decision context */}
      {evaluation && (
        <div className="mb-6">
          <DecisionContext
            decision={evaluation.decision}
            scoreTotal={evaluation.score_total}
            hasCriticalBlock={factoresDetail.some((f) => f.is_critical_block)}
          />
        </div>
      )}

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
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Acciones requeridas ({evaluation.acciones_sugeridas.length})
          </h2>
          <div className="space-y-3">
            {evaluation.acciones_sugeridas.map((accion, i) => {
              const relatedFactor = factoresConRiesgo.find((f) =>
                accion.toLowerCase().includes(f.factor_code.split("_")[0])
              ) ?? factoresConRiesgo[i] ?? factoresConRiesgo[0];
              return (
                <ActionCard key={i} accion={accion} relatedFactor={relatedFactor} index={i} />
              );
            })}
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
