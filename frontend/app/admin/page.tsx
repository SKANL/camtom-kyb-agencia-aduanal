"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { api, type SatImportRun } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const LIST_TYPES = ["art_69", "art_69b", "art_69b_bis"] as const;

export default function AdminPage() {
  const [runs, setRuns] = useState<SatImportRun[]>([]);
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api.listSatImportRuns().then(setRuns).catch(() => {});
  }, []);

  async function triggerImport(listType: string) {
    setLoading((prev) => ({ ...prev, [listType]: true }));
    try {
      await api.triggerSatImport(listType);
      const updated = await api.listSatImportRuns();
      setRuns(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al importar");
    } finally {
      setLoading((prev) => ({ ...prev, [listType]: false }));
    }
  }

  const lastRun = (listType: string) => runs.find((r) => r.list_type === listType);

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">← Inicio</Link>
          <h1 className="text-2xl font-bold mt-2">Admin — Listas SAT</h1>
        </div>

        <div className="space-y-4">
          {LIST_TYPES.map((listType) => {
            const run = lastRun(listType);
            const isLoading = loading[listType];
            return (
              <div key={listType} className="rounded-lg border border-border bg-card p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium font-mono text-sm">{listType}</p>
                  {run ? (
                    <p className="text-xs text-muted-foreground mt-1">
                      {run.rows_imported !== null ? `${run.rows_imported} registros` : "En progreso"}
                      {" · "}
                      {run.finished_at ? new Date(run.finished_at).toLocaleString("es-MX") : "—"}
                    </p>
                  ) : (
                    <p className="text-xs text-muted-foreground mt-1">Sin importar</p>
                  )}
                  {isLoading && <Progress className="mt-2 h-1 w-32" value={null} />}
                </div>
                <Button
                  onClick={() => triggerImport(listType)}
                  disabled={isLoading}
                  className="bg-primary text-primary-foreground"
                  size="sm"
                >
                  {isLoading ? "Importando…" : "Actualizar"}
                </Button>
              </div>
            );
          })}
        </div>

        <div className="mt-8">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Historial de importaciones</h2>
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-card">
                <tr>
                  <th className="text-left px-3 py-2 text-muted-foreground">Lista</th>
                  <th className="text-left px-3 py-2 text-muted-foreground">Estado</th>
                  <th className="text-right px-3 py-2 text-muted-foreground">Registros</th>
                  <th className="text-right px-3 py-2 text-muted-foreground">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {runs.length === 0 && (
                  <tr><td colSpan={4} className="px-3 py-4 text-center text-muted-foreground">Sin historial</td></tr>
                )}
                {runs.map((run) => (
                  <tr key={run.id} className="border-t border-border">
                    <td className="px-3 py-2 font-mono">{run.list_type}</td>
                    <td className="px-3 py-2">{run.status}</td>
                    <td className="px-3 py-2 text-right">{run.rows_imported ?? "—"}</td>
                    <td className="px-3 py-2 text-right">{run.started_at ? new Date(run.started_at).toLocaleDateString("es-MX") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
