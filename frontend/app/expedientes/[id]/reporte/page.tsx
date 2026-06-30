"use client";
import { use } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import useSWR from "swr";
import { api, type EvaluationResult, type ConsultaSat, type EvaluationHistoryEntry } from "@/lib/api-client";
import { useExpediente } from "@/hooks/use-expediente";
import { useLatestEvaluation } from "@/hooks/use-expediente";
import { ScoreGauge } from "@/components/ScoreGauge";
import { FactorDetailCard } from "@/components/FactorDetailCard";
import { StepperHeader } from "@/components/StepperHeader";
import { ScoreBreakdown } from "@/components/ScoreBreakdown";
import { DecisionContext } from "@/components/DecisionContext";
import { ActionCard } from "@/components/ActionCard";
import { SatEvidenceSection } from "@/components/SatEvidenceSection";
import { EvaluationHistory } from "@/components/EvaluationHistory";
import { ComplianceContext } from "@/components/ComplianceContext";
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

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  processing: "Procesando",
  completed: "Completado",
  needs_update: "Requiere actualización",
  review_required: "En revisión",
};

function buildNarrative(
  evaluation: EvaluationResult,
  razonSocial: string
): string {
  const { decision, score_total, factores_detail } = evaluation;
  const criticals = factores_detail.filter((f) => f.is_critical_block && f.points > 0);
  const risks = factores_detail.filter((f) => !f.is_critical_block && f.points > 0);

  if (decision === "safe") {
    if (risks.length === 0 && criticals.length === 0) {
      return `${razonSocial} superó todas las verificaciones sin señales de riesgo. El RFC no aparece en ninguna lista fiscal del SAT (Art. 69, 69-B ni 69-B Bis), los documentos presentados son consistentes entre sí y están completos. El score acumulado es ${score_total} puntos, por debajo del umbral de alerta (< 30 pts). La empresa cumple los criterios de la Regla 1.4.14 RGCE 2026 para operar en comercio exterior.`;
    }
    return `${razonSocial} obtuvo un score de ${score_total} puntos. Se detectaron ${risks.length} observación(es) menores (${risks.map((f) => FACTOR_LABELS[f.factor_code] ?? f.factor_code).join(", ")}), pero ninguna supera el umbral crítico ni activa bloqueo automático. La empresa puede operar bajo monitoreo continuo.`;
  }

  if (decision === "high_risk") {
    if (criticals.length > 0) {
      return `${razonSocial} no puede operar en comercio exterior bajo la Regla 1.4.14 RGCE 2026. Se activó bloqueo automático por ${criticals.length} factor(es) crítico(s): ${criticals.map((f) => FACTOR_LABELS[f.factor_code] ?? f.factor_code).join("; ")}. La presencia en listas fiscales del SAT o discrepancias irreconciliables constituyen impedimento absoluto independientemente del score total (${score_total} pts).`;
    }
    return `${razonSocial} acumula ${score_total} puntos de riesgo, superando el umbral crítico de 70 pts. Los factores de mayor impacto son: ${risks
      .slice(0, 3)
      .map((f) => FACTOR_LABELS[f.factor_code] ?? f.factor_code)
      .join(", ")}. Se requiere resolución de los puntos observados antes de autorizar operaciones de comercio exterior.`;
  }

  return `${razonSocial} acumula ${score_total} puntos de riesgo (umbral de alerta: 30–69 pts). Se detectaron ${risks.length + criticals.length} factor(es) que requieren verificación manual: ${[...criticals, ...risks]
    .slice(0, 3)
    .map((f) => FACTOR_LABELS[f.factor_code] ?? f.factor_code)
    .join(", ")}. La empresa puede continuar el proceso sujeto a revisión documental adicional por parte del agente aduanal.`;
}

function NeedsUpdateBanner({
  expedienteId,
  onEvaluated,
}: {
  expedienteId: string;
  onEvaluated?: () => void;
}) {
  return (
    <div className="rounded-xl border border-warning/40 bg-warning/5 px-5 py-4 flex items-start gap-3 mb-6">
      <AlertTriangle className="size-5 text-warning shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-semibold text-warning">El expediente requiere actualización</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          Uno o más documentos han cambiado o vencido desde la última evaluación. Re-evaluá para obtener un resultado actualizado.
        </p>
      </div>
      <EvaluateButton expedienteId={expedienteId} onEvaluated={onEvaluated} />
    </div>
  );
}

export default function ReportePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const { expediente, isLoading: loadingExpediente } = useExpediente(id);
  const { evaluation, mutate: mutateEvaluation } = useLatestEvaluation(id);
  const { data: consultas = [] } = useSWR<ConsultaSat[]>(
    `consultas-sat-report-${id}`,
    () => api.listConsultasSat(id).catch(() => [])
  );
  const { data: historialEvals = [] } = useSWR<EvaluationHistoryEntry[]>(
    `evaluations-history-${id}`,
    () => api.listEvaluations(id).catch(() => [])
  );

  if (loadingExpediente) {
    return (
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="space-y-4">
          <div className="h-8 w-64 rounded-lg bg-muted animate-pulse" />
          <div className="h-48 rounded-xl bg-card border border-border animate-pulse" />
          <div className="h-48 rounded-xl bg-card border border-border animate-pulse" />
        </div>
      </main>
    );
  }
  if (!expediente) {
    return (
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <p className="text-muted-foreground">Expediente no encontrado.</p>
          <Link href="/" className="text-primary hover:underline mt-2 block">← Volver</Link>
        </div>
      </main>
    );
  }

  const factoresDetail = evaluation?.factores_detail ?? [];
  const factoresInformativos = evaluation?.factores_informativos ?? [];
  const factoresConRiesgo = factoresDetail
    .filter((f) => f.points > 0)
    .sort((a, b) => b.points - a.points);
  const factoresSinRiesgo = factoresDetail.filter((f) => f.points === 0);
  const maxPoints = factoresConRiesgo.length
    ? Math.max(...factoresConRiesgo.map((f) => f.points))
    : 100;

  const narrative = evaluation ? buildNarrative(evaluation, expediente.razon_social) : null;

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <StepperHeader currentStep={4} expedienteId={id} />

      {/* Breadcrumb */}
      <div className="mb-6">
        <Link href={`/expedientes/${id}`} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          ← {expediente.razon_social}
        </Link>
        <h1 className="text-2xl font-bold mt-2">Reporte KYB</h1>
        <p className="text-muted-foreground text-sm mt-1 font-mono">{expediente.rfc}</p>
      </div>

      {expediente.status === "needs_update" && (
        <NeedsUpdateBanner expedienteId={id} onEvaluated={() => mutateEvaluation()} />
      )}

      {/* Score hero */}
      <div className="rounded-xl border border-border bg-card p-6 mb-6">
        {evaluation ? (
          <ScoreGauge score={evaluation.score_total} decision={evaluation.decision} />
        ) : (
          <div className="text-center py-4 space-y-3">
            <p className="text-muted-foreground text-sm">
              Aún no hay evaluación. Cargá los documentos y ejecutá la evaluación KYB.
            </p>
            <EvaluateButton expedienteId={id} onEvaluated={() => mutateEvaluation()} />
          </div>
        )}
      </div>

      {/* Plain-language narrative */}
      {narrative && (
        <div className="rounded-xl border border-border bg-card p-6 mb-6">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            ¿Por qué esta decisión?
          </h2>
          <p className="text-sm leading-relaxed">{narrative}</p>

          <details className="mt-4">
            <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors select-none">
              Ver umbrales de clasificación
            </summary>
            <div className="mt-3 rounded-lg bg-muted/40 p-3 text-xs space-y-1.5">
              <p>
                <span className="inline-block w-28 text-muted-foreground">Safe (aprobado):</span>
                Score &lt; 30 pts y sin bloqueos críticos
              </p>
              <p>
                <span className="inline-block w-28 text-muted-foreground">Revisión:</span>
                30 ≤ Score &lt; 70 pts o indicios menores
              </p>
              <p>
                <span className="inline-block w-28 text-muted-foreground">Alto riesgo:</span>
                Score ≥ 70 pts o bloqueo crítico activo
              </p>
              <p className="text-muted-foreground/70 pt-1">
                Bloqueos críticos: presencia en Art. 69-B definitivos, RFC inválido, o discrepancia irreconciliable entre documentos.
              </p>
            </div>
          </details>
        </div>
      )}

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

      {/* SAT evidence */}
      {consultas.length > 0 && (
        <SatEvidenceSection consultas={consultas} />
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
                <ActionCard key={i} accion={accion} relatedFactor={relatedFactor} index={i} expedienteId={id} />
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

      {/* Informational notes — factors that don't score but need manual attention */}
      {factoresInformativos.length > 0 && (
        <section className="mb-6">
          <div className="rounded-xl border border-border bg-muted/30 p-5 space-y-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Notas informativas
            </p>
            <p className="text-xs text-muted-foreground">
              Los siguientes puntos no afectan el score pero requieren atención manual del agente aduanal.
            </p>
            <ul className="space-y-2">
              {factoresInformativos.map((f) => (
                <li key={f.factor_code} className="flex items-start gap-2.5 text-sm">
                  <span className="mt-0.5 size-4 rounded-full bg-muted-foreground/20 flex items-center justify-center shrink-0 text-[10px] text-muted-foreground font-bold">
                    i
                  </span>
                  <span className="text-muted-foreground leading-relaxed">{f.detail}</span>
                  {f.legal_ref && (
                    <span className="text-xs text-muted-foreground/50 shrink-0 mt-0.5">
                      ({f.legal_ref})
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
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
            <dd>{STATUS_LABEL[expediente.status] ?? expediente.status}</dd>
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

      {/* Evaluation history (only shown if >1 evaluation) */}
      {historialEvals.length > 1 && (
        <section className="mb-6">
          <EvaluationHistory entries={historialEvals} />
        </section>
      )}

      {/* Legal + compliance context */}
      <section className="mb-6">
        <ComplianceContext />
      </section>

      {/* Actions */}
      <div className="flex gap-3 flex-wrap">
        <EvaluateButton expedienteId={id} onEvaluated={() => mutateEvaluation()} />
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
