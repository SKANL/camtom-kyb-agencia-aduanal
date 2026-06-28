"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export default function NuevoExpedientePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    razon_social: "",
    rfc: "",
    domicilio_fiscal: "",
    representante_legal: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const expediente = await api.createExpediente(form);
      router.push(`/expedientes/${expediente.id}/reporte`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear expediente");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-md mx-auto">
        <div className="mb-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">← Volver</Link>
          <h1 className="text-2xl font-bold mt-2">Nuevo expediente</h1>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <Label htmlFor="razon_social">Razón social</Label>
            <Input id="razon_social" value={form.razon_social} onChange={(e) => setForm({ ...form, razon_social: e.target.value })} required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="rfc">RFC</Label>
            <Input id="rfc" value={form.rfc} onChange={(e) => setForm({ ...form, rfc: e.target.value.toUpperCase() })} required className="mt-1 font-mono" />
          </div>
          <div>
            <Label htmlFor="domicilio_fiscal">Domicilio fiscal</Label>
            <Input id="domicilio_fiscal" value={form.domicilio_fiscal} onChange={(e) => setForm({ ...form, domicilio_fiscal: e.target.value })} className="mt-1" />
          </div>
          <div>
            <Label htmlFor="representante_legal">Representante legal</Label>
            <Input id="representante_legal" value={form.representante_legal} onChange={(e) => setForm({ ...form, representante_legal: e.target.value })} className="mt-1" />
          </div>
          {error && <p className="text-destructive text-sm">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full bg-primary text-primary-foreground">
            {loading ? "Creando…" : "Crear expediente"}
          </Button>
        </form>
      </div>
    </main>
  );
}
