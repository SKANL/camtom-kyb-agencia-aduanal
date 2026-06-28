"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";

export function EvaluateButton({ expedienteId }: { expedienteId: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleEvaluate() {
    setLoading(true);
    setError(null);
    try {
      await api.evaluate(expedienteId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al evaluar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        onClick={handleEvaluate}
        disabled={loading}
        className="inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all disabled:opacity-50"
      >
        {loading ? "Evaluando…" : "Evaluar ahora"}
      </button>
      {error && <p className="text-destructive text-xs mt-1">{error}</p>}
    </div>
  );
}
