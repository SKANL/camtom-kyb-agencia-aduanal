import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import type React from "react";
import type { Decision } from "@/lib/api-client";

const DECISION_CONFIG: Record<
  Decision,
  {
    icon: React.ReactNode;
    title: string;
    summary: string;
    implication: string;
    nextSteps: string[];
    borderClass: string;
    bgClass: string;
    iconClass: string;
  }
> = {
  safe: {
    icon: <CheckCircle2 className="size-5" />,
    title: "Perfil aprobado",
    summary: "El cliente no presenta hallazgos en listas fiscales del SAT ni discrepancias documentales significativas.",
    implication: "Puede proceder con la inscripción al Padrón de Importadores/Exportadores conforme a la Regla 1.4.14 RGCE 2026.",
    nextSteps: [
      "Archivar el expediente y emitir constancia de revisión KYB.",
      "Inscribir al cliente en el padrón si cumple los demás requisitos operativos.",
      "Programar revisión periódica (recomendado: cada 6 meses o ante cambio de situación fiscal).",
    ],
    borderClass: "border-success/40",
    bgClass: "bg-success/5",
    iconClass: "text-success",
  },
  review_required: {
    icon: <AlertTriangle className="size-5" />,
    title: "Revisión manual requerida",
    summary: "Se detectaron factores de riesgo que no bloquean automáticamente la operación pero exigen diligencia ampliada.",
    implication: "No se puede inscribir al cliente sin resolver primero los hallazgos identificados. El agente aduanal debe documentar las acciones correctivas tomadas.",
    nextSteps: [
      "Ejecutar las acciones requeridas listadas en la sección siguiente.",
      "Solicitar documentación adicional o aclaración ante el SAT según corresponda.",
      "Re-evaluar el expediente una vez resueltos los hallazgos.",
      "Documentar el proceso de diligencia en el expediente físico.",
    ],
    borderClass: "border-warning/40",
    bgClass: "bg-warning/5",
    iconClass: "text-warning",
  },
  high_risk: {
    icon: <XCircle className="size-5" />,
    title: "Alto riesgo — no operar",
    summary: "El RFC del cliente está vinculado a un bloqueo crítico (EFOS definitivo u otro hallazgo grave) que impide la operación bajo cualquier circunstancia.",
    implication: "Operar con este cliente expone a la agencia a responsabilidad solidaria por créditos fiscales inválidos y sanciones del SAT. No inscribir al padrón hasta resolver el bloqueo.",
    nextSteps: [
      "Notificar al cliente de manera formal y documentar la comunicación.",
      "Si el cliente impugna, solicitar resolución formal del SAT que acredite la desvirtuación del listado.",
      "No emitir ni aceptar CFDIs relacionados con este RFC hasta obtener resolución favorable.",
      "Consultar al área jurídica de la agencia antes de cualquier acción adicional.",
    ],
    borderClass: "border-destructive/40",
    bgClass: "bg-destructive/5",
    iconClass: "text-destructive",
  },
};

type Props = {
  decision: Decision;
  scoreTotal: number;
  hasCriticalBlock: boolean;
};

export function DecisionContext({ decision, scoreTotal, hasCriticalBlock }: Props) {
  const cfg = DECISION_CONFIG[decision];

  return (
    <div className={`rounded-xl border ${cfg.borderClass} ${cfg.bgClass} p-5 space-y-4`}>
      <div className="flex items-start gap-3">
        <span className={cfg.iconClass}>{cfg.icon}</span>
        <div className="space-y-1">
          <p className={`text-base font-semibold ${cfg.iconClass}`}>{cfg.title}</p>
          <p className="text-sm text-foreground/90 leading-relaxed">{cfg.summary}</p>
        </div>
      </div>

      {/* Score explanation */}
      <div className="rounded-lg bg-background/60 px-4 py-3 space-y-1">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          ¿Cómo se calculó este resultado?
        </p>
        <p className="text-sm text-foreground/80 leading-relaxed">
          El sistema acumuló{" "}
          <span className="font-semibold">{scoreTotal} puntos de riesgo</span> sumando los factores
          detectados. Scores por debajo de 30 son aprobados, entre 30 y 69 requieren revisión, y 70 o
          más resultan en bloqueo.{" "}
          {hasCriticalBlock && (
            <span className="text-destructive font-medium">
              Además, se activó al menos un factor de bloqueo crítico (puntaje máximo automático).
            </span>
          )}
        </p>
      </div>

      {/* Operational implication */}
      <div className="flex items-start gap-2">
        <Info className="size-4 shrink-0 mt-0.5 text-muted-foreground" />
        <p className="text-sm text-muted-foreground leading-relaxed">{cfg.implication}</p>
      </div>

      {/* Next steps */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Pasos recomendados
        </p>
        <ol className="space-y-1.5">
          {cfg.nextSteps.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
              <span className="shrink-0 w-5 h-5 rounded-full bg-muted flex items-center justify-center text-xs font-semibold text-muted-foreground mt-0.5">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      {/* What would change the outcome */}
      {decision === "review_required" && (
        <div className="rounded-lg bg-warning/5 border border-warning/20 px-3 py-2.5 space-y-1.5">
          <p className="text-xs font-semibold text-warning uppercase tracking-wide">
            Para cambiar a Aprobado
          </p>
          <p className="text-xs text-foreground/80 leading-relaxed">
            Resolvé todos los factores de riesgo listados abajo. Una vez que no haya
            discrepancias, documentos faltantes ni problemas de completitud, el score
            bajaría a 0 pts y la decisión cambiaría a <strong>Aprobado</strong>.
          </p>
        </div>
      )}
      {decision === "high_risk" && (
        <div className="rounded-lg bg-destructive/5 border border-destructive/20 px-3 py-2.5 space-y-1.5">
          <p className="text-xs font-semibold text-destructive uppercase tracking-wide">
            Para cambiar esta decisión
          </p>
          <p className="text-xs text-foreground/80 leading-relaxed">
            Si hay un bloqueo crítico (RFC en EFOS definitivo), la decisión no cambia
            con solo corregir documentos — el cliente debe obtener una resolución de
            desvirtuación emitida por el SAT. Contactá al área jurídica.
          </p>
        </div>
      )}
      {decision === "safe" && (
        <div className="rounded-lg bg-success/5 border border-success/20 px-3 py-2.5">
          <p className="text-xs text-success leading-relaxed">
            El expediente cumple todos los requisitos de la Regla 1.4.14 RGCE 2026.
            Podés proceder con la inscripción al padrón de importadores/exportadores.
          </p>
        </div>
      )}
    </div>
  );
}
