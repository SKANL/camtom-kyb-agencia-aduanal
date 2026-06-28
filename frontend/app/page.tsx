import Link from "next/link";
import { api, type Expediente } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";

const DECISION_BADGE: Record<string, { label: string; className: string }> = {
  safe: { label: "Safe", className: "bg-success text-white" },
  review_required: { label: "Review required", className: "bg-warning text-background" },
  high_risk: { label: "High risk", className: "bg-destructive text-white" },
};

export default async function DashboardPage() {
  let expedientes: Expediente[] = [];
  try {
    expedientes = await api.listExpedientes();
  } catch {
    // Backend may not be reachable at build time
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Expedientes KYB</h1>
          <Link href="/expedientes/nuevo" className="inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none bg-primary text-primary-foreground hover:bg-primary/80 h-8 gap-1.5 px-2.5">
            + Nuevo expediente
          </Link>
        </div>

        {expedientes.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <p className="text-lg">No hay expedientes registrados.</p>
            <p className="text-sm mt-2">Crea el primer expediente para comenzar.</p>
          </div>
        ) : (
          <div className="rounded-lg border border-border overflow-hidden">
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
                    <tr key={e.id} className="border-t border-border hover:bg-card/50 transition-colors">
                      <td className="px-4 py-3 font-medium">
                        <Link href={`/expedientes/${e.id}/reporte`} className="hover:text-primary transition-colors">
                          {e.razon_social}
                        </Link>
                      </td>
                      <td className="px-4 py-3 font-mono text-muted-foreground">{e.rfc}</td>
                      <td className="px-4 py-3 text-muted-foreground capitalize">{e.status}</td>
                      <td className="px-4 py-3">
                        {badge ? (
                          <Badge className={badge.className}>{badge.label}</Badge>
                        ) : (
                          <span className="text-muted-foreground text-xs">Pendiente</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        {e.score_total !== null ? `${e.score_total} pts` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
