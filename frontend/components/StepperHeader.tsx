import Link from "next/link";

const STEPS = [
  { n: 1, label: "Datos empresa", href: (_id?: string) => "/expedientes/nuevo" },
  { n: 2, label: "Documentos",    href: (id?: string) => id ? `/expedientes/${id}` : "#" },
  { n: 3, label: "Revisión",      href: (id?: string) => id ? `/expedientes/${id}` : "#" },
  { n: 4, label: "Reporte KYB",   href: (id?: string) => id ? `/expedientes/${id}/reporte` : "#" },
] as const;

export function StepperHeader({
  currentStep,
  expedienteId,
}: {
  currentStep: 1 | 2 | 3 | 4;
  expedienteId?: string;
}) {
  return (
    <nav className="flex items-center gap-0 mb-8">
      {STEPS.map((step, i) => {
        const done = step.n < currentStep;
        const active = step.n === currentStep;
        const href = done ? step.href(expedienteId) : undefined;

        const circle = (
          <div
            className={[
              "w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-colors",
              done
                ? "bg-primary border-primary text-primary-foreground"
                : active
                ? "border-primary text-primary bg-primary/10"
                : "border-border text-muted-foreground bg-card",
            ].join(" ")}
          >
            {done ? (
              <svg viewBox="0 0 12 10" className="size-3 fill-none stroke-current stroke-2">
                <polyline points="1,5 4,8 11,1" />
              </svg>
            ) : (
              step.n
            )}
          </div>
        );

        return (
          <div key={step.n} className="flex items-center gap-0 flex-1 min-w-0">
            <div className="flex flex-col items-center gap-1 shrink-0">
              {href ? (
                <Link href={href} className="hover:opacity-80 transition-opacity">
                  {circle}
                </Link>
              ) : (
                circle
              )}
              <span
                className={[
                  "text-xs whitespace-nowrap hidden sm:inline",
                  active ? "text-primary font-medium" : done ? "text-foreground" : "text-muted-foreground",
                ].join(" ")}
              >
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={[
                  "flex-1 h-px mx-2 mt-[-12px]",
                  done ? "bg-primary" : "bg-border",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
