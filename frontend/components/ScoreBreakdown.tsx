import type { FactorDetail } from "@/lib/api-client";

type Props = {
  factores: FactorDetail[];
  scoreTotal: number;
};

const CATEGORY_CONFIG = {
  sat: {
    label: "Listas SAT",
    description: "Art. 69, 69-B y 69-B Bis CFF",
    color: "bg-destructive",
    textColor: "text-destructive",
    bgColor: "bg-destructive/10",
  },
  discrepancia: {
    label: "Discrepancias",
    description: "Inconsistencias entre documentos",
    color: "bg-warning",
    textColor: "text-warning",
    bgColor: "bg-warning/10",
  },
  completitud: {
    label: "Completitud",
    description: "Documentos y campos faltantes",
    color: "bg-primary",
    textColor: "text-primary",
    bgColor: "bg-primary/10",
  },
} as const;

export function ScoreBreakdown({ factores, scoreTotal }: Props) {
  const byCategory = {
    sat: factores.filter((f) => f.category === "sat").reduce((s, f) => s + f.points, 0),
    discrepancia: factores.filter((f) => f.category === "discrepancia").reduce((s, f) => s + f.points, 0),
    completitud: factores.filter((f) => f.category === "completitud").reduce((s, f) => s + f.points, 0),
  };

  const total = byCategory.sat + byCategory.discrepancia + byCategory.completitud;

  if (total === 0) return null;

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        Desglose por categoría
      </p>
      <div className="grid grid-cols-3 gap-3">
        {(Object.entries(byCategory) as [keyof typeof CATEGORY_CONFIG, number][]).map(([cat, pts]) => {
          const cfg = CATEGORY_CONFIG[cat];
          return (
            <div key={cat} className={`rounded-lg p-3 ${cfg.bgColor} space-y-1`}>
              <p className={`text-xs font-medium ${cfg.textColor}`}>{cfg.label}</p>
              <p className={`text-2xl font-bold leading-none ${cfg.textColor}`}>{pts}</p>
              <p className="text-xs text-muted-foreground leading-tight">{cfg.description}</p>
            </div>
          );
        })}
      </div>

      {/* Stacked bar */}
      <div className="h-2 rounded-full overflow-hidden bg-muted flex">
        {total > 0 && (
          <>
            <div className="bg-destructive" style={{ width: `${(byCategory.sat / total) * 100}%` }} />
            <div className="bg-warning" style={{ width: `${(byCategory.discrepancia / total) * 100}%` }} />
            <div className="bg-primary" style={{ width: `${(byCategory.completitud / total) * 100}%` }} />
          </>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Total acumulado: <span className="font-semibold text-foreground">{scoreTotal} puntos</span>
        {scoreTotal > 100 && (
          <span className="ml-2 text-warning">(por encima de 100 — factor crítico activo)</span>
        )}
      </p>
    </div>
  );
}
