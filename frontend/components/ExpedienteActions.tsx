"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Expediente } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Pencil, Trash2 } from "lucide-react";

type Props = {
  expediente: Pick<
    Expediente,
    "id" | "razon_social" | "rfc" | "domicilio_fiscal" | "representante_legal"
  >;
  redirectOnDelete?: boolean;
};

export function ExpedienteActions({ expediente, redirectOnDelete = false }: Props) {
  const router = useRouter();

  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editFields, setEditFields] = useState({
    razon_social: expediente.razon_social ?? "",
    rfc: expediente.rfc ?? "",
    domicilio_fiscal: expediente.domicilio_fiscal ?? "",
    representante_legal: expediente.representante_legal ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleEdit() {
    setSaving(true);
    setError(null);
    try {
      await api.updateExpediente(expediente.id, {
        razon_social: editFields.razon_social || undefined,
        rfc: editFields.rfc || undefined,
        domicilio_fiscal: editFields.domicilio_fiscal || undefined,
        representante_legal: editFields.representante_legal || undefined,
      });
      setEditOpen(false);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await api.deleteExpediente(expediente.id);
      setDeleteOpen(false);
      if (redirectOnDelete) {
        router.push("/");
      } else {
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => { setError(null); setEditOpen(true); }}
          aria-label="Editar expediente"
        >
          <Pencil className="size-3.5" />
        </Button>
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => { setError(null); setDeleteOpen(true); }}
          aria-label="Eliminar expediente"
          className="text-destructive hover:bg-destructive/10"
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>

      {/* Edit dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar expediente</DialogTitle>
            <DialogDescription>
              Modificá los datos del expediente. El RFC se normaliza a mayúsculas.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-1">
            {(
              [
                { key: "razon_social", label: "Razón social" },
                { key: "rfc", label: "RFC" },
                { key: "domicilio_fiscal", label: "Domicilio fiscal" },
                { key: "representante_legal", label: "Representante legal" },
              ] as const
            ).map(({ key, label }) => (
              <div key={key}>
                <label className="text-xs text-muted-foreground block mb-1">{label}</label>
                <input
                  value={editFields[key]}
                  onChange={(e) =>
                    setEditFields({ ...editFields, [key]: e.target.value })
                  }
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
            ))}
            {error && <p className="text-destructive text-xs">{error}</p>}
          </div>

          <DialogFooter>
            <DialogClose render={<Button variant="outline" />} disabled={saving}>
              Cancelar
            </DialogClose>
            <Button onClick={handleEdit} disabled={saving}>
              {saving ? "Guardando…" : "Guardar cambios"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar expediente</DialogTitle>
            <DialogDescription>
              Esta acción es irreversible. Se eliminará el expediente{" "}
              <strong>{expediente.razon_social}</strong> junto con todos sus documentos,
              evaluaciones y registros de auditoría.
            </DialogDescription>
          </DialogHeader>

          {error && <p className="text-destructive text-xs px-1">{error}</p>}

          <DialogFooter>
            <DialogClose render={<Button variant="outline" />} disabled={deleting}>
              Cancelar
            </DialogClose>
            <Button
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/80"
            >
              {deleting ? "Eliminando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
