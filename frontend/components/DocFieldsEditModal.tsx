"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api-client";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

const FIELD_LABELS: Record<string, string> = {
  rfc: "RFC",
  razon_social: "Razón social",
  fecha_emision: "Fecha de emisión (YYYY-MM-DD)",
  nombre_completo: "Nombre completo",
  nombre_representante: "Nombre del representante",
  rfc_agente_aduanal: "RFC del agente aduanal",
  domicilio_fiscal: "Domicilio fiscal",
  domicilio: "Domicilio",
  fecha_vencimiento: "Fecha de vencimiento (YYYY-MM-DD)",
  fecha_vigencia: "Fecha de vigencia (YYYY-MM-DD)",
  alcance: "Alcance",
};

type Props = {
  documentoId: string;
  expedienteId: string;
  missingFields: string[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
};

export function DocFieldsEditModal({
  documentoId,
  expedienteId,
  missingFields,
  open,
  onOpenChange,
  onSaved,
}: Props) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(missingFields.map((f) => [f, ""]))
  );
  const [currentFields, setCurrentFields] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    api.getDocumento(expedienteId, documentoId).then((doc) => {
      if (doc?.fields) {
        setCurrentFields(doc.fields as Record<string, unknown>);
        const prefilled: Record<string, string> = {};
        for (const f of missingFields) {
          const existing = (doc.fields as Record<string, unknown>)[f];
          prefilled[f] = existing != null ? String(existing) : "";
        }
        setValues(prefilled);
      }
    }).catch(() => {});
  }, [open, documentoId, expedienteId, missingFields]);

  async function handleSave() {
    setSaving(true);
    try {
      const updates: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(values)) {
        updates[k] = v || null;
      }
      const merged = { ...currentFields, ...updates };
      await api.reviewDocumento(documentoId, merged);
      toast.success("Campos actualizados — podés re-evaluar el expediente");
      onSaved();
      onOpenChange(false);
    } catch {
      toast.error("Error al guardar los campos");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Completar campos faltantes</DialogTitle>
        </DialogHeader>
        <p className="text-xs text-muted-foreground -mt-2 mb-1">
          Completá los campos requeridos para que el expediente pueda ser evaluado correctamente.
        </p>
        <div className="space-y-3 py-1">
          {missingFields.map((field) => (
            <div key={field}>
              <label className="text-xs text-muted-foreground mb-1 block font-medium">
                {FIELD_LABELS[field] ?? field}{" "}
                <span className="text-destructive">*</span>
              </label>
              <Input
                value={values[field] ?? ""}
                onChange={(e) =>
                  setValues((v) => ({ ...v, [field]: e.target.value }))
                }
                placeholder={`Ingresá ${FIELD_LABELS[field] ?? field}`}
                className="text-sm"
              />
            </div>
          ))}
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Guardando…" : "Guardar cambios"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
