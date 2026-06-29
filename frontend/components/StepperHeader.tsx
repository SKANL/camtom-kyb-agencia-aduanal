const STEPS = [
  { n: 1, label: "Datos empresa" },
  { n: 2, label: "Documentos" },
  { n: 3, label: "Revisión" },
  { n: 4, label: "Reporte KYB" },
] as const;

export function StepperHeader({ currentStep }: { currentStep: 1 | 2 | 3 | 4 }) {
  return (
    <nav className="flex items-center gap-0 mb-8">
      {STEPS.map((step, i) => {
        const done = step.n < currentStep;
        const active = step.n === currentStep;
        return (
          <div key={step.n} className="flex items-center gap-0 flex-1 min-w-0">
            <div className="flex flex-col items-center gap-1 shrink-0">
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
                {done ? "✓" : step.n}
              </div>
              <span
                className={[
                  "text-xs whitespace-nowrap",
                  active ? "text-primary font-medium" : "text-muted-foreground",
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
