import { api, type Expediente } from "@/lib/api-client";
import { ExpedientesList } from "@/components/ExpedientesList";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let initialExpedientes: Expediente[] = [];
  try {
    initialExpedientes = await api.listExpedientes();
  } catch {
    // Backend unreachable at build time
  }

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
      <ExpedientesList initialExpedientes={initialExpedientes} />
    </main>
  );
}
