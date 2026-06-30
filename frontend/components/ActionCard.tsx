import { ShieldAlert, AlertTriangle, FolderSearch, FileCheck2, Scale, Clock, ArrowRight, Database } from "lucide-react";
import Link from "next/link";
import type React from "react";
import type { FactorDetail } from "@/lib/api-client";

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  sat: <ShieldAlert className="size-4 text-destructive shrink-0 mt-0.5" />,
  discrepancia: <AlertTriangle className="size-4 text-warning shrink-0 mt-0.5" />,
  completitud: <FolderSearch className="size-4 text-primary shrink-0 mt-0.5" />,
  otro: <FileCheck2 className="size-4 text-muted-foreground shrink-0 mt-0.5" />,
};

const PRIORITY_LABEL: Record<string, { label: string; className: string }> = {
  sat: { label: "Bloqueo / alta prioridad", className: "bg-destructive/15 text-destructive" },
  discrepancia: { label: "Prioridad media", className: "bg-warning/15 text-warning" },
  completitud: { label: "Prioridad estándar", className: "bg-primary/15 text-primary" },
  otro: { label: "Informativo", className: "bg-muted text-muted-foreground" },
};

type DetailedAction = {
  summary: string;
  steps: string[];
  urgency?: string;
};

const FACTOR_ACTIONS: Record<string, DetailedAction> = {
  sat_69b_definitivo: {
    summary: "No operar bajo ninguna circunstancia hasta obtener resolución formal del SAT.",
    steps: [
      "Verificar la presencia en el listado definitivo (verificado contra datos SAT importados en este sistema).",
      "Notificar formalmente al cliente por escrito y documentar la comunicación en el expediente.",
      "Consultar al área jurídica de la agencia antes de cualquier acción adicional.",
      "No emitir ni aceptar CFDIs vinculados a este RFC.",
      "Si el cliente impugna, solicitar la resolución de desvirtuación emitida por el SAT antes de reabrir el expediente.",
    ],
    urgency: "Inmediato — no postergar",
  },
  sat_69b_presunto: {
    summary: "RFC en proceso de revisión SAT por presunta emisión de CFDI sin respaldo.",
    steps: [
      "Verificar el estado actual (verificado contra datos SAT importados en este sistema).",
      "Iniciar diligencia ampliada: solicitar al cliente carta de no vinculación con CFDIs observados.",
      "Esperar la resolución del SAT antes de proceder a la inscripción en el padrón.",
      "Documentar cada paso del proceso en el expediente físico.",
    ],
    urgency: "Antes de continuar el onboarding",
  },
  sat_69b_bis: {
    summary: "RFC en el listado de transmisión indebida de pérdidas fiscales.",
    steps: [
      "Verificar la presencia en el listado 69-B Bis (verificado contra datos SAT importados en este sistema).",
      "Solicitar al cliente aclaración escrita ante el SAT sobre las pérdidas fiscales cuestionadas.",
      "Obtener resolución del SAT que aclare la situación antes de inscribir al padrón.",
    ],
    urgency: "Antes de inscripción al padrón",
  },
  sat_69_incumplido: {
    summary: "Contribuyente con obligaciones fiscales incumplidas según el SAT.",
    steps: [
      "Verificar la categoría de incumplimiento (verificado contra datos SAT importados en este sistema).",
      "Requerir al cliente aclaración de situación fiscal y documentación que acredite la resolución del adeudo.",
      "No inscribir al padrón hasta obtener constancia de situación fiscal limpia.",
    ],
    urgency: "Antes de inscripción al padrón",
  },
  disc_rfc: {
    summary: "El RFC no coincide entre los documentos del expediente.",
    steps: [
      "Identificar cuál documento tiene el RFC diferente (revisar CSF, acta constitutiva, poder notarial).",
      "Solicitar al cliente la versión corregida del documento con error.",
      "Reemplazar el documento corregido en el expediente y volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la evaluación final",
  },
  disc_razon_social: {
    summary: "La razón social no coincide entre los documentos del expediente.",
    steps: [
      "Identificar qué documento tiene la variación (abreviatura societaria vs nombre completo, typo, etc.).",
      "Si la diferencia es solo abreviatura societaria (SA de CV vs S.A. de C.V.), documentar la aclaración.",
      "Si es un nombre diferente, solicitar al cliente el documento corregido.",
      "Recargar el documento corregido y volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la evaluación final",
  },
  disc_domicilio: {
    summary: "El domicilio fiscal no coincide entre los documentos.",
    steps: [
      "Comparar el domicilio en la CSF, el comprobante de domicilio y el formulario del expediente.",
      "Si hay cambio de domicilio reciente, solicitar CSF actualizada al cliente.",
      "Actualizar los campos del expediente con el domicilio vigente y volver a evaluar.",
    ],
    urgency: "Antes de la evaluación final",
  },
  disc_representante: {
    summary: "El nombre del representante legal no coincide entre poder, identificación y formulario.",
    steps: [
      "Comparar el nombre exactamente entre el poder notarial, la identificación oficial y el encargo conferido.",
      "Solicitar al cliente aclaración escrita si difieren (nombre compuesto vs abreviado).",
      "Si hay error en algún documento, solicitar la versión corregida.",
    ],
    urgency: "Antes de la evaluación final",
  },
  disc_fechas: {
    summary: "Inconsistencias de fechas entre documentos del expediente.",
    steps: [
      "Revisar las fechas de emisión y vigencia en cada documento.",
      "Verificar que el comprobante de domicilio tenga menos de 90 días.",
      "Verificar que la CSF corresponda al mes calendario vigente.",
      "Solicitar documentos actualizados para los que estén vencidos.",
    ],
    urgency: "Antes de la evaluación final",
  },
  doc_missing: {
    summary: "Hay uno o más documentos requeridos que no han sido cargados.",
    steps: [
      "Identificar qué documento falta en la sección 'Estado de documentos' del expediente.",
      "Solicitar al cliente el documento faltante.",
      "Cargar el PDF desde la zona de arrastre o con el botón de carga.",
      "Volver a ejecutar la evaluación una vez cargado.",
    ],
    urgency: "Antes de la evaluación final",
  },
  doc_expired: {
    summary: "El comprobante de domicilio tiene más de 90 días de antigüedad.",
    steps: [
      "Solicitar al cliente un comprobante de domicilio reciente (máximo 90 días: recibo CFE, TELMEX, agua, estado de cuenta bancario).",
      "Reemplazar el documento en el expediente.",
      "Volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la inscripción al padrón",
  },
  csf_stale: {
    summary: "La CSF no corresponde al mes calendario vigente.",
    steps: [
      "El cliente debe generar una nueva CSF desde el portal del SAT (mi.sat.gob.mx → RFC y CSF → Genera tu CSF).",
      "Reemplazar la CSF en el expediente con la versión del mes actual.",
      "Volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la inscripción al padrón",
  },
  manifestacion_incompleta: {
    summary: "La Manifestación bajo Protesta no incluye la cláusula de los Art. 69-B y 49 Bis CFF.",
    steps: [
      "Revisar el template de la Manifestación bajo Protesta de Decir Verdad.",
      "Verificar que incluya explícitamente la declaración de no encontrarse en los listados del Art. 69-B CFF y Art. 49 Bis CFF.",
      "Solicitar al cliente que firme la versión correcta del documento.",
      "Reemplazar el documento en el expediente y volver a revisar los campos extraídos.",
    ],
    urgency: "Antes de la evaluación final",
  },
  socios_incompletos: {
    summary: "No se registraron socios, accionistas ni beneficiario controlador del acta constitutiva.",
    steps: [
      "Revisar el acta constitutiva para identificar a todos los socios y sus porcentajes de participación.",
      "Registrar a cada socio con nombre completo, RFC y porcentaje desde la pantalla de revisión del documento.",
      "Identificar al beneficiario controlador (persona física con ≥25% del capital o control efectivo).",
      "Volver a ejecutar la evaluación.",
    ],
    urgency: "Requerido por LFPIORPI y Regla 1.4.14 RGCE",
  },
  rep_legal_incompleto: {
    summary: "No se capturó el nombre completo del representante legal.",
    steps: [
      "Revisar la identificación oficial del representante legal y capturar el nombre completo.",
      "Confirmar que coincide con el nombre en el poder notarial.",
      "Guardar la revisión y volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de la evaluación final",
  },
  rfc_formato_invalido: {
    summary: "El RFC no cumple con el formato oficial mexicano.",
    steps: [
      "Verificar el RFC en la CSF (fuente primaria oficial).",
      "Corregir el RFC en los datos del expediente.",
      "Volver a ejecutar la evaluación.",
    ],
    urgency: "Antes de cualquier consulta SAT",
  },
};

function getNavLink(
  factorCode: string,
  expedienteId: string,
  evidence?: Record<string, unknown> | null
): { href: string; label: string } | null {
  if (factorCode === "doc_missing" && evidence?.doc_type) {
    return { href: `/expedientes/${expedienteId}`, label: "Ir al expediente → cargar documento" };
  }
  if (factorCode.startsWith("disc_") || factorCode.startsWith("doc_")) {
    return { href: `/expedientes/${expedienteId}`, label: "Ir al expediente" };
  }
  if (factorCode === "csf_stale" || factorCode === "doc_expired") {
    return { href: `/expedientes/${expedienteId}`, label: "Ir al expediente → reemplazar documento" };
  }
  return null;
}

type Props = {
  accion: string;
  relatedFactor?: FactorDetail;
  index: number;
  expedienteId: string;
};

export function ActionCard({ accion, relatedFactor, index, expedienteId }: Props) {
  const category = relatedFactor?.category ?? "otro";
  const icon = CATEGORY_ICON[category];
  const priority = PRIORITY_LABEL[category];
  const detail = relatedFactor ? FACTOR_ACTIONS[relatedFactor.factor_code] : undefined;

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground mt-0.5">
          {index + 1}
        </div>
        {icon}
        <div className="flex-1 space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${priority.className}`}>
              {priority.label}
            </span>
            {detail?.urgency && (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="size-3" />
                {detail.urgency}
              </span>
            )}
          </div>
          <p className="text-sm font-medium leading-snug">{detail?.summary ?? accion}</p>
        </div>
      </div>

      {/* Specific steps */}
      {detail?.steps && detail.steps.length > 0 && (
        <ol className="space-y-1.5 ml-9">
          {detail.steps.map((step, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-foreground/80 leading-relaxed">
              <span className="shrink-0 font-semibold text-muted-foreground mt-0.5">{i + 1}.</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      )}

      {/* Legal ref */}
      {relatedFactor?.legal_ref && (
        <div className="flex items-start gap-1.5 ml-9">
          <Scale className="size-3 shrink-0 mt-0.5 text-muted-foreground" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            {relatedFactor.legal_ref}
          </p>
        </div>
      )}

      {/* Contextual nav for doc/disc factors */}
      {(() => {
        const nav = relatedFactor
          ? getNavLink(relatedFactor.factor_code, expedienteId, relatedFactor.evidence)
          : null;
        return nav ? (
          <div className="ml-9">
            <Link
              href={nav.href}
              className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
            >
              <ArrowRight className="size-3" />
              {nav.label}
            </Link>
          </div>
        ) : null;
      })()}

      {/* SAT data note for sat_* factors */}
      {relatedFactor?.category === "sat" && relatedFactor.factor_code !== "art_49bis_no_verificable" && (
        <div className="ml-9 flex items-start gap-1.5">
          <Database className="size-3 shrink-0 mt-0.5 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">
            Verificado contra datos SAT importados en este sistema
          </p>
        </div>
      )}
    </div>
  );
}
