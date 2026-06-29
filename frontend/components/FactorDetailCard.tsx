import { ShieldAlert, BookOpen, ChevronDown } from "lucide-react";
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
  doc_expired: "Comprobante de domicilio vencido (más de 90 días)",
  csf_stale: "Constancia de Situación Fiscal desactualizada",
  doc_data_incomplete: "Campos obligatorios incompletos en documento",
  manifestacion_incompleta: "Manifestación bajo protesta incompleta",
  socios_incompletos: "Socios o beneficiario controlador no registrados",
  rep_legal_incompleto: "Representante legal sin nombre completo",
};

const DOC_TYPE_LABELS: Record<string, string> = {
  csf: "Constancia de Situación Fiscal",
  acta_constitutiva: "Acta Constitutiva",
  comprobante_domicilio: "Comprobante de Domicilio",
  identificacion_rep_legal: "Identificación del Representante Legal",
  poder_notarial: "Poder Notarial",
  encargo_conferido: "Encargo Conferido",
  manifestacion_protesta: "Manifestación bajo Protesta de Decir Verdad",
  rfc: "Comprobante de RFC",
};

const CATEGORY_CHIP: Record<string, { label: string; className: string }> = {
  sat: { label: "Listas SAT", className: "bg-destructive/15 text-destructive" },
  discrepancia: { label: "Discrepancia documental", className: "bg-warning/15 text-warning" },
  completitud: { label: "Completitud del expediente", className: "bg-primary/15 text-primary" },
  otro: { label: "Otro", className: "bg-muted text-muted-foreground" },
};

function EvidenceDisplay({ evidence }: { evidence: Record<string, unknown> }) {
  const entries = Object.entries(evidence);
  return (
    <div className="space-y-1">
      {entries.map(([k, v]) => {
        if (k === "doc_type" && typeof v === "string") {
          return (
            <p key={k} className="text-xs text-muted-foreground">
              Documento afectado: <span className="font-medium text-foreground">{DOC_TYPE_LABELS[v] ?? v}</span>
            </p>
          );
        }
        if (k === "manual_review_required" && v === true) {
          return (
            <p key={k} className="text-xs text-warning font-medium">
              Requiere revisión manual por el agente aduanal
            </p>
          );
        }
        if (k === "documento_id") {
          return (
            <p key={k} className="text-xs text-muted-foreground">
              Documento con campos incompletos — revisión manual recomendada
            </p>
          );
        }
        // Fallback for unknown keys: render as readable text, never raw JSON
        return (
          <p key={k} className="text-xs text-muted-foreground capitalize">
            {k.replace(/_/g, " ")}: <span className="font-medium text-foreground">{String(v)}</span>
          </p>
        );
      })}
    </div>
  );
}

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
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {isCritical && (
              <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold bg-destructive text-background">
                <ShieldAlert className="size-3" />
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
          <p className="text-xs text-muted-foreground">pts de riesgo</p>
        </div>
      </div>

      {/* Progress bar */}
      {factor.points > 0 && (
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full ${isCritical ? "bg-destructive" : "bg-warning"}`}
            style={{ width: `${barPct}%` }}
          />
        </div>
      )}

      {/* Detail text */}
      <p className="text-sm text-foreground/90 leading-relaxed">{factor.detail}</p>

      {/* Human-readable evidence */}
      {factor.evidence && Object.keys(factor.evidence).length > 0 && (
        <div className="rounded-lg bg-muted/40 px-3 py-2">
          <EvidenceDisplay evidence={factor.evidence} />
        </div>
      )}

      {/* Legal citation — expanded by default for high-severity factors */}
      {factor.legal_ref && (
        <details className="group" open={isCritical || factor.points >= 35}>
          <summary className="flex items-center gap-1.5 cursor-pointer text-xs text-muted-foreground hover:text-foreground transition-colors select-none list-none">
            <BookOpen className="size-3.5 shrink-0" />
            <span>Fundamento legal</span>
            <ChevronDown className="size-3 transition-transform group-open:rotate-180 ml-auto" />
          </summary>
          <div className="mt-2 rounded-lg bg-muted/60 px-3 py-2">
            <p className="text-xs text-muted-foreground leading-relaxed">{factor.legal_ref}</p>
          </div>
        </details>
      )}
    </div>
  );
}
