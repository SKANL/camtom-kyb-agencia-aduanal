import Link from "next/link";
import { Suspense } from "react";
import { api, type Expediente } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";

const DECISION_BADGE: Record<string, { label: string; className: string }> = {
  safe: { label: "Safe", className: "bg-success text-background" },
  review_required: { label: "Review required", className: "bg-warning text-background" },
  high_risk: { label: "High risk", className: "bg-destructive text-background" },
};

function KpiCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">{label}</p>
      <p className="text-3xl font-bold text-primary">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  );
}

async function ExpedientesContent() {
  let expedientes: Expediente[] = [];
  try {
    expedientes = await api.listExpedientes();
  } catch {
    // Backend unreachable at build time — render empty state
  }

  const safe = expedientes.filter((e) => e.decision === "safe").length;
  const flagged = expedientes.filter(
    (e) => e.decision === "review_required" || e.decision === "high_risk"
  ).length;
  const pending = expedientes.filter((e) => !e.decision).length;

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <KpiCard label="Total expedientes" value={expedientes.length} />
        <KpiCard label="Aprobados" value={safe} sub="safe ✓" />
        <KpiCard
          label="Requieren atención"
          value={flagged + pending}
          sub={pending > 0 ? `${pending} sin evaluar` : ""}
        />
      </div>

      {expedientes.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <p className="text-lg font-medium mb-2">Sin expedientes registrados</p>
          <p className="text-sm">Crea el primero para comenzar el proceso KYB.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-card">
              <tr>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Cliente</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">RFC</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Estado</th>
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Decisión</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              {expedientes.map((e) => {
                const badge = e.decision ? DECISION_BADGE[e.decision] : null;
                return (
                  <tr
                    key={e.id}
                    className="border-t border-border hover:bg-card/60 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium">
                      <Link
                        href={`/expedientes/${e.id}/reporte`}
                        className="hover:text-primary transition-colors"
                      >
                        {e.razon_social}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-muted-foreground text-xs">
                      {e.rfc}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground capitalize text-xs">
                      {e.status}
                    </td>
                    <td className="px-4 py-3">
                      {badge ? (
                        <Badge className={badge.className}>{badge.label}</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">Sin evaluar</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm">
                      {e.score_total !== null ? (
                        <span className="text-primary font-bold">{e.score_total} pts</span>
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
      )}
    </>
  );
}

export default function DashboardPage() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Expedientes KYB</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Evaluación de riesgo — Regla 1.4.14 RGCE 2026
          </p>
        </div>
        <Link
          href="/expedientes/nuevo"
          className="inline-flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all"
        >
          + Nuevo expediente
        </Link>
      </div>
      <Suspense fallback={
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[0,1,2].map(i => <div key={i} className="h-24 rounded-xl bg-card animate-pulse" />)}
        </div>
      }>
        <ExpedientesContent />
      </Suspense>
    </main>
  );
}
