import type { EvaluationHistoryEntry, Decision } from "@/lib/api-client";
import { History, TrendingUp, TrendingDown, Minus } from "lucide-react";

const DECISION_LABEL: Record<Decision, { label: string; className: string }> = {
  safe: { label: "Aprobado", className: "text-success" },
  review_required: { label: "Revisión", className: "text-warning" },
  high_risk: { label: "Alto riesgo", className: "text-destructive" },
};

function TrendIcon({ current, prev }: { current: number; prev: number }) {
  if (current < prev) return <TrendingDown className="size-3.5 text-success" />;
  if (current > prev) return <TrendingUp className="size-3.5 text-destructive" />;
  return <Minus className="size-3.5 text-muted-foreground" />;
}

export function EvaluationHistory({ entries }: { entries: EvaluationHistoryEntry[] }) {
  if (entries.length <= 1) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <History className="size-4 text-muted-foreground" />
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Historial de evaluaciones
        </p>
      </div>

      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-3 py-2 text-muted-foreground font-medium">Fecha</th>
              <th className="text-center px-3 py-2 text-muted-foreground font-medium">Decisión</th>
              <th className="text-right px-3 py-2 text-muted-foreground font-medium">Score</th>
              <th className="text-center px-3 py-2 text-muted-foreground font-medium">Tendencia</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, i) => {
              const cfg = DECISION_LABEL[entry.decision];
              const nextEntry = entries[i + 1];
              return (
                <tr key={entry.id} className="border-t border-border">
                  <td className="px-3 py-2 text-muted-foreground">
                    {new Date(entry.created_at).toLocaleString("es-MX", {
                      day: "2-digit", month: "short", year: "numeric",
                      hour: "2-digit", minute: "2-digit",
                    })}
                    {i === 0 && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-primary/10 text-primary px-1.5 py-0.5 text-[10px] font-medium">
                        Actual
                      </span>
                    )}
                  </td>
                  <td className={`px-3 py-2 text-center font-semibold ${cfg.className}`}>
                    {cfg.label}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-semibold">
                    {entry.score_total} pts
                  </td>
                  <td className="px-3 py-2 text-center">
                    {nextEntry ? (
                      <div className="flex items-center justify-center gap-1">
                        <TrendIcon current={entry.score_total} prev={nextEntry.score_total} />
                        <span className="text-muted-foreground">
                          {entry.score_total > nextEntry.score_total
                            ? `+${entry.score_total - nextEntry.score_total}`
                            : entry.score_total < nextEntry.score_total
                            ? `-${nextEntry.score_total - entry.score_total}`
                            : "="}
                        </span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
