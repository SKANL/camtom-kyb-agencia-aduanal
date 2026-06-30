"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { useExpedientes } from "@/hooks/use-expedientes";
import { ExpedientesList } from "@/components/ExpedientesList";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function DashboardPage() {
  const { data: expedientes = [], mutate } = useExpedientes();
  const [seeding, setSeeding] = useState(false);

  async function handleSeedDemo() {
    setSeeding(true);
    try {
      await api.seedDemo();
      toast.success("3 expedientes demo cargados y evaluados");
      await mutate();
    } catch {
      toast.error("Error al cargar datos de demo");
    } finally {
      setSeeding(false);
    }
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
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSeedDemo}
            disabled={seeding}
            title="Recarga los 3 expedientes demo (limpia los anteriores)"
          >
            {seeding ? "…" : "Demo"}
          </Button>
          <Link
            href="/expedientes/nuevo"
            className="inline-flex items-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all"
          >
            + Nuevo expediente
          </Link>
        </div>
      </div>

      {expedientes.length === 0 && !seeding ? (
        <div className="text-center py-12 space-y-4">
          <p className="text-muted-foreground">No hay expedientes. Comenzá cargando los datos de demo.</p>
          <Button onClick={handleSeedDemo} disabled={seeding} className="bg-primary text-primary-foreground">
            {seeding ? "Cargando…" : "Cargar datos de demo"}
          </Button>
        </div>
      ) : (
        <ExpedientesList initialExpedientes={expedientes} />
      )}
    </main>
  );
}
