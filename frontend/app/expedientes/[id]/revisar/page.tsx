"use client";
import { use, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

export default function RevisarPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ documento_id?: string }>;
}) {
  const { id } = use(params);
  const { documento_id } = use(searchParams);

  const [fields, setFields] = useState<Record<string, string>>({
    razon_social: "",
    rfc: "",
    domicilio_fiscal: "",
  });
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmar() {
    if (!documento_id) return;
    setLoading(true);
    setError(null);
    try {
      await api.reviewDocumento(documento_id, fields);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <main className="min-h-screen bg-background text-foreground p-8 flex items-center justify-center">
        <div className="text-center">
          <p className="text-success text-2xl mb-4">✓ Revisión guardada</p>
          <Link href={`/expedientes/${id}/reporte`} className="text-primary hover:underline">
            Ver reporte →
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">← Volver</Link>
          <h1 className="text-2xl font-bold mt-2">Revisión humana de extracción</h1>
          {documento_id && <p className="text-xs text-muted-foreground mt-1 font-mono">Doc: {documento_id}</p>}
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-sm text-muted-foreground mb-2">Preview del documento</p>
            <div className="bg-surface-elevated rounded p-8 text-center text-muted-foreground text-xs">
              PDF preview (iframe al signed URL de Storage)
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-4 space-y-4">
            <p className="text-sm font-medium mb-2">Campos extraídos — confirmar o corregir</p>
            {Object.entries(fields).map(([campo, valor]) => (
              <div key={campo}>
                <Label htmlFor={campo} className="text-xs text-muted-foreground">{campo}</Label>
                <Textarea
                  id={campo}
                  value={valor}
                  onChange={(e) => setFields({ ...fields, [campo]: e.target.value })}
                  className="mt-1 text-sm"
                  rows={2}
                />
              </div>
            ))}
            {error && <p className="text-destructive text-xs">{error}</p>}
            <Button
              onClick={confirmar}
              disabled={loading || !documento_id}
              className="w-full bg-primary text-primary-foreground"
            >
              {loading ? "Guardando…" : "Confirmar revisión"}
            </Button>
          </div>
        </div>
      </div>
    </main>
  );
}
