import { ShieldAlert, AlertTriangle, FolderSearch, FileCheck2, Scale } from "lucide-react";
import type React from "react";
import type { FactorDetail } from "@/lib/api-client";

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  sat: <ShieldAlert className="size-4 text-destructive shrink-0 mt-0.5" />,
  discrepancia: <AlertTriangle className="size-4 text-warning shrink-0 mt-0.5" />,
  completitud: <FolderSearch className="size-4 text-primary shrink-0 mt-0.5" />,
  otro: <FileCheck2 className="size-4 text-muted-foreground shrink-0 mt-0.5" />,
};

const PRIORITY_LABEL: Record<string, { label: string; className: string }> = {
  sat: { label: "Prioridad alta", className: "bg-destructive/15 text-destructive" },
  discrepancia: { label: "Prioridad media", className: "bg-warning/15 text-warning" },
  completitud: { label: "Prioridad estándar", className: "bg-primary/15 text-primary" },
  otro: { label: "Informativo", className: "bg-muted text-muted-foreground" },
};

type Props = {
  accion: string;
  relatedFactor?: FactorDetail;
  index: number;
};

export function ActionCard({ accion, relatedFactor, index }: Props) {
  const category = relatedFactor?.category ?? "otro";
  const icon = CATEGORY_ICON[category];
  const priority = PRIORITY_LABEL[category];

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl border border-border bg-card">
      <div className="shrink-0 w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground mt-0.5">
        {index + 1}
      </div>
      {icon}
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${priority.className}`}>
            {priority.label}
          </span>
        </div>
        <p className="text-sm font-medium leading-snug">{accion}</p>
        {relatedFactor?.legal_ref && (
          <div className="flex items-start gap-1.5">
            <Scale className="size-3 shrink-0 mt-0.5 text-muted-foreground" />
            <p className="text-xs text-muted-foreground leading-relaxed">
              {relatedFactor.legal_ref.split(" — ")[0]}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
