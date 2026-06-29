import Link from "next/link";
import { api } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { EvaluateButton } from "./EvaluateButton";

const DECISION_META: Record<
  string,
  { label: string; badgeClass: string; desc: string }
> = {
  safe: {
    label: "Safe",
    badgeClass: "bg-success text-background",
    desc: "Score dentro del umbral de operación normal. Sin alertas en listas SAT.",
  },
  review_required: {
    label: "Review required",
    badgeClass: "bg-warning text-background",
    desc: "Existen factores que requieren revisión adicional antes de operar.",
  },
  high_risk: {
    label: "High risk",
    badgeClass: "bg-destructive text-background",
    desc: "Score supera el umbral crítico. No operar hasta resolver las alertas.",
  },
};

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

  const decisionMeta = expediente.decision
    ? DECISION_META[expediente.decision]
    : null;

  const factores = evaluation?.factores_score
    ? Object.entries(evaluation.factores_score)
    : [];
  const maxPoints = factores.length
    ? Math.max(...factores.map(([, v]) => v), 1)
    : 100;

  const factoresConPuntos = factores.filter(([, v]) => v > 0);
  const factoresSinPuntos = factores.filter(([, v]) => v === 0);

  return (
    <main className="max-w-3xl mx-auto px-6 py-8">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href={`/expedientes/${id}`}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          ← {expediente.razon_social}
        </Link>
        <h1 className="text-2xl font-bold mt-2">Reporte KYB</h1>
      </div>

      {/* Score hero */}
      <div className="rounded-xl border border-border bg-card p-6 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">
              Decisión
            </p>
            {decisionMeta ? (
              <>
                <Badge className={`text-base px-3 py-1 ${decisionMeta.badgeClass}`}>
                  {decisionMeta.label}
                </Badge>
                <p className="text-sm text-muted-foreground max-w-xs">
                  {decisionMeta.desc}
                </p>
              </>
            ) : (
              <p className="text-muted-foreground">Sin evaluar</p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Score de riesgo
            </p>
            <p className="text-5xl font-bold text-primary leading-none">
              {expediente.score_total ?? "—"}
            </p>
            {expediente.score_total !== null && (
              <p className="text-sm text-muted-foreground mt-1">puntos</p>
            )}
          </div>
        </div>
      </div>

      {/* Factors breakdown */}
      {factores.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6 mb-6">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-4">
            Desglose de factores de riesgo
          </h2>

          {factoresConPuntos.length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-muted-foreground mb-2">
                Factores que suman puntos de riesgo
              </p>
              <div className="divide-y divide-border">
                {factoresConPuntos.map(([code, points]) => (
                  <FactorRow
                    key={code}
                    code={code}
                    points={points}
                    maxPoints={maxPoints}
                  />
                ))}
              </div>
            </div>
          )}

          {factoresSinPuntos.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground mb-2">
                Sin impacto en score
              </p>
              <div className="divide-y divide-border">
                {factoresSinPuntos.map(([code, points]) => (
                  <FactorRow
                    key={code}
                    code={code}
                    points={points}
                    maxPoints={maxPoints}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Acciones sugeridas */}
      {evaluation?.acciones_sugeridas &&
        evaluation.acciones_sugeridas.length > 0 && (
          <div className="rounded-xl border border-border bg-card p-6 mb-6">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
              Acciones sugeridas
            </h2>
            <ul className="space-y-2">
              {evaluation.acciones_sugeridas.map((accion) => (
                <li key={accion} className="flex items-start gap-2 text-sm">
                  <span className="text-warning mt-0.5 shrink-0">›</span>
                  <span>{accion}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

      {/* Datos del expediente */}
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
      <div className="flex gap-3">
        <EvaluateButton expedienteId={id} />
        <Link
          href={`/expedientes/${id}`}
          className="inline-flex items-center justify-center rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted transition-all"
        >
          Ver documentos
        </Link>
      </div>
    </main>
  );
}
