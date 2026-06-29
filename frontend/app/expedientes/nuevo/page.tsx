"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { revalidateExpedientes } from "@/hooks/use-expedientes";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { StepperHeader } from "@/components/StepperHeader";

const RFC_REGEX = /^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$/;

export default function NuevoExpedientePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    razon_social: "",
    rfc: "",
    domicilio_fiscal: "",
    representante_legal: "",
  });
  const [rfcError, setRfcError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function validateRfc(value: string): string | null {
    if (!value) return null;
    if (!RFC_REGEX.test(value))
      return "RFC inválido. Formato: 3-4 letras + 6 dígitos fecha + 3 caracteres homoclave (ej: EKU9003173C9)";
    return null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const rfcErr = validateRfc(form.rfc);
    if (rfcErr) { setRfcError(rfcErr); return; }
    setLoading(true);
    setError(null);
    try {
      const expediente = await api.createExpediente(form);
      await revalidateExpedientes();
      router.push(`/expedientes/${expediente.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear expediente");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-lg mx-auto">
        <StepperHeader currentStep={1} />

        <div className="mb-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">
            ← Volver al dashboard
          </Link>
          <h1 className="text-2xl font-bold mt-2">Datos de la empresa</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Ingresá los datos básicos del cliente para iniciar el expediente KYB.
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <Label htmlFor="razon_social">
              Razón social <span className="text-destructive">*</span>
            </Label>
            <Input
              id="razon_social"
              placeholder="Ej: Empresa Ejemplo SA de CV"
              value={form.razon_social}
              onChange={(e) => setForm({ ...form, razon_social: e.target.value })}
              required
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="rfc">
              RFC <span className="text-destructive">*</span>
            </Label>
            <Input
              id="rfc"
              placeholder="Ej: EKU9003173C9"
              value={form.rfc}
              onChange={(e) => {
                const val = e.target.value.toUpperCase();
                setForm({ ...form, rfc: val });
                setRfcError(validateRfc(val));
              }}
              required
              className={`mt-1 font-mono ${rfcError ? "border-destructive" : ""}`}
            />
            {rfcError && <p className="text-destructive text-xs mt-1">{rfcError}</p>}
            {form.rfc && !rfcError && (
              <p className="text-success text-xs mt-1">✓ Formato RFC válido</p>
            )}
          </div>

          <div>
            <Label htmlFor="domicilio_fiscal">Domicilio fiscal</Label>
            <Input
              id="domicilio_fiscal"
              placeholder="Ej: Av. Insurgentes Sur 123, Col. Roma, CDMX"
              value={form.domicilio_fiscal}
              onChange={(e) => setForm({ ...form, domicilio_fiscal: e.target.value })}
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="representante_legal">Representante legal</Label>
            <Input
              id="representante_legal"
              placeholder="Ej: Juan Pérez García"
              value={form.representante_legal}
              onChange={(e) => setForm({ ...form, representante_legal: e.target.value })}
              className="mt-1"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2">
              <p className="text-destructive text-sm">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            disabled={loading || !!rfcError}
            className="w-full bg-primary text-primary-foreground"
          >
            {loading ? "Creando expediente…" : "Continuar — Cargar documentos →"}
          </Button>
        </form>
      </div>
    </main>
  );
}
