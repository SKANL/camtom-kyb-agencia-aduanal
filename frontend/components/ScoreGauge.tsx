type Decision = "safe" | "review_required" | "high_risk";

const DECISION_CONFIG: Record<Decision, { label: string; color: string; textClass: string }> = {
  safe: { label: "Aprobado", color: "bg-success", textClass: "text-success" },
  review_required: { label: "Requiere revisión", color: "bg-warning", textClass: "text-warning" },
  high_risk: { label: "Alto riesgo", color: "bg-destructive", textClass: "text-destructive" },
};

export function ScoreGauge({ score, decision }: { score: number; decision: string }) {
  const config = DECISION_CONFIG[decision as Decision] ?? DECISION_CONFIG.high_risk;
  const pct = Math.min(Math.max(score, 0), 100);

  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Score de riesgo</p>
          <p className={`text-5xl font-bold leading-none ${config.textClass}`}>
            {score}
            <span className="text-sm font-normal text-muted-foreground ml-1">pts de riesgo</span>
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Decisión</p>
          <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${config.color} text-background`}>
            {config.label}
          </span>
        </div>
      </div>

      <div className="relative h-3 rounded-full overflow-hidden bg-muted">
        <div className="absolute inset-0 flex">
          <div className="bg-success/30" style={{ width: "30%" }} />
          <div className="bg-warning/30" style={{ width: "40%" }} />
          <div className="bg-destructive/30" style={{ width: "30%" }} />
        </div>
        <div
          className={`absolute top-0 left-0 h-full rounded-full transition-all duration-500 ${config.color}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="flex justify-between text-xs text-muted-foreground">
        <span className="text-success">0–29 aprobado</span>
        <span className="text-warning">30–69 revisión</span>
        <span className="text-destructive">70+ bloqueado</span>
      </div>
    </div>
  );
}
