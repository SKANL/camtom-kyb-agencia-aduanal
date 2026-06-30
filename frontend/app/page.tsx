"use client";
import Link from "next/link";
import { useExpedientes } from "@/hooks/use-expedientes";
import { ExpedientesList } from "@/components/ExpedientesList";

export default function DashboardPage() {
  const { data: expedientes = [] } = useExpedientes();

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
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

      {expedientes.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No hay expedientes aún.</p>
          <Link
            href="/expedientes/nuevo"
            className="inline-flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all mt-4"
          >
            + Crear primer expediente
          </Link>
        </div>
      ) : (
        <ExpedientesList initialExpedientes={expedientes} />
      )}
    </main>
  );
}
