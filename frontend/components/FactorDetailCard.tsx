import type { FactorDetail } from "@/lib/api-client";

const FACTOR_LABELS: Record<string, string> = {
  sat_69b_definitivo: "EFOS Definitivo (Art. 69-B CFF)",
  sat_69b_presunto: "EFOS Presunto (Art. 69-B CFF)",
  sat_69b_bis: "Pérdidas fiscales indebidas (Art. 69-B Bis CFF)",
  sat_69_incumplido: "Contribuyente incumplido (Art. 69 CFF)",
  rfc_formato_invalido: "RFC con formato inválido",
  art_49bis_no_verificable: "Art. 49 Bis CFF — sin lista pública verificable",
  disc_rfc: "Discrepancia de RFC entre documentos",
  disc_razon_social: "Discrepancia de razón social",
  disc_domicilio: "Discrepancia de domicilio fiscal",
  disc_representante: "Discrepancia del representante legal",
  disc_fechas: "Inconsistencia de fechas",
  doc_missing: "Documento requerido faltante",
  doc_expired: "Comprobante de domicilio vencido (>90 días)",
  csf_stale: "Constancia de Situación Fiscal desactualizada",
  doc_data_incomplete: "Campos obligatorios incompletos en documento",
  manifestacion_incompleta: "Manifestación bajo protesta incompleta",
  socios_incompletos: "Socios / beneficiario controlador no registrados",
  rep_legal_incompleto: "Representante legal sin nombre completo",
};

const CATEGORY_CHIP: Record<string, { label: string; className: string }> = {
  sat: { label: "SAT", className: "bg-destructive/15 text-destructive" },
  discrepancia: { label: "Discrepancia", className: "bg-warning/15 text-warning" },
  completitud: { label: "Completitud", className: "bg-primary/15 text-primary" },
  otro: { label: "Otro", className: "bg-muted text-muted-foreground" },
};

export function FactorDetailCard({
  factor,
  maxPoints,
}: {
  factor: FactorDetail;
  maxPoints: number;
}) {
  const chip = CATEGORY_CHIP[factor.category] ?? CATEGORY_CHIP.otro;
  const label = FACTOR_LABELS[factor.factor_code] ?? factor.factor_code;
  const barPct = maxPoints > 0 ? Math.round((factor.points / maxPoints) * 100) : 0;
  const isCritical = factor.is_critical_block;

  return (
    <div
      className={[
        "rounded-xl border p-4 space-y-3 transition-colors",
        isCritical
          ? "border-destructive/50 bg-destructive/5"
          : factor.points > 0
          ? "border-warning/30 bg-card"
          : "border-border bg-card/50",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {isCritical && (
              <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-destructive text-background">
                BLOQUEO CRÍTICO
              </span>
            )}
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${chip.className}`}>
              {chip.label}
            </span>
          </div>
          <p className="text-sm font-semibold leading-snug">{label}</p>
        </div>
        <div className="shrink-0 text-right">
          <p
            className={`text-2xl font-bold leading-none ${
              isCritical ? "text-destructive" : factor.points > 0 ? "text-warning" : "text-success"
            }`}
          >
            {factor.points > 0 ? `+${factor.points}` : "0"}
          </p>
          <p className="text-xs text-muted-foreground">puntos</p>
        </div>
      </div>

      {factor.points > 0 && (
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full ${isCritical ? "bg-destructive" : "bg-warning"}`}
            style={{ width: `${barPct}%` }}
          />
        </div>
      )}

      <p className="text-sm text-foreground/90 leading-relaxed">{factor.detail}</p>

      {factor.legal_ref && (
        <div className="flex items-start gap-2 rounded-lg bg-muted/60 px-3 py-2">
          <span className="text-muted-foreground mt-0.5 shrink-0 text-xs">§</span>
          <p className="text-xs text-muted-foreground leading-relaxed">{factor.legal_ref}</p>
        </div>
      )}

      {factor.evidence && Object.keys(factor.evidence).length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer hover:text-foreground transition-colors">
            Ver evidencia técnica
          </summary>
          <pre className="mt-1 rounded bg-muted px-2 py-1 text-xs overflow-auto">
            {JSON.stringify(factor.evidence, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
