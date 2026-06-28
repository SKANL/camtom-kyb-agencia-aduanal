const PASOS = [
  "Extrayendo texto del PDF",
  "Validando contra esquema",
  "Consultando listas del SAT",
  "Calculando score",
] as const;

export function PipelineStatus({ pasoActual }: { pasoActual: number }) {
  return (
    <ul className="space-y-2 text-sm">
      {PASOS.map((paso, i) => {
        const done = i < pasoActual;
        const current = i === pasoActual;
        return (
          <li
            key={paso}
            className={
              done
                ? "text-success flex items-center gap-2"
                : current
                ? "text-primary flex items-center gap-2 animate-pulse"
                : "text-muted-foreground flex items-center gap-2"
            }
          >
            <span className="w-4 text-center">{done ? "✓" : current ? "›" : "·"}</span>
            <span>{paso}{current ? "…" : ""}</span>
          </li>
        );
      })}
    </ul>
  );
}
