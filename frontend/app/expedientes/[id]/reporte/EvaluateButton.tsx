"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { revalidateExpedientes } from "@/hooks/use-expedientes";
import { toast } from "sonner";
import { RefreshCw } from "lucide-react";

export function EvaluateButton({
  expedienteId,
  onEvaluated,
}: {
  expedienteId: string;
  onEvaluated?: () => void;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleEvaluate() {
    setLoading(true);
    setError(null);
    try {
      await api.evaluate(expedienteId);
      await revalidateExpedientes();
      toast.success("Evaluación completada");
      if (onEvaluated) {
        onEvaluated();
      } else {
        router.refresh();
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al evaluar";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        onClick={handleEvaluate}
        disabled={loading}
        className="inline-flex items-center gap-2 justify-center rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/80 transition-all disabled:opacity-50"
      >
        <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
        {loading ? "Evaluando…" : "Evaluar ahora"}
      </button>
      {error && <p className="text-destructive text-xs mt-1">{error}</p>}
    </div>
  );
}
