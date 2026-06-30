import { Scale, BookOpen, Database } from "lucide-react";

const REGLAS = [
  {
    titulo: "Regla 1.4.14 RGCE 2026",
    descripcion: "Requisito base que obliga a las agencias aduanales a verificar que sus clientes no figuren en las listas de contribuyentes incumplidos o EFOS del SAT antes de inscribirlos al Padrón de Importadores/Exportadores.",
    url: null,
    localData: false,
  },
  {
    titulo: "Art. 69 CFF — Contribuyentes incumplidos",
    descripcion: "Listado de personas físicas y morales con créditos fiscales firmes, exigibles, CSD sin efectos, o no localizadas. Presencia en este listado genera 25 pts de riesgo.",
    url: null,
    localData: true,
  },
  {
    titulo: "Art. 69-B CFF — EFOS (Empresas Facturadoras de Operaciones Simuladas)",
    descripcion: "El SAT publica dos sub-listados: 'presuntos' (proceso de revisión, 40 pts de riesgo) y 'definitivos' (bloqueo crítico — no operar bajo ninguna circunstancia, 100 pts). La desvirtualización ante el SAT es el único camino para salir del listado definitivo.",
    url: null,
    localData: true,
  },
  {
    titulo: "Art. 69-B Bis CFF — Transmisión indebida de pérdidas",
    descripcion: "Listado de contribuyentes que transfirieron pérdidas fiscales de forma indebida. Genera 35 pts de riesgo. Requiere aclaración ante el SAT y resolución formal antes de operar.",
    url: null,
    localData: true,
  },
  {
    titulo: "Art. 49 Bis CFF — Contrabando técnico",
    descripcion: "No tiene lista pública consultable al día de hoy. El sistema lo documenta como limitación conocida y lo marca como 'revisión manual requerida'. No genera puntos de riesgo automáticos.",
    url: null,
    localData: false,
  },
  {
    titulo: "LFPIORPI — Beneficiario Controlador",
    descripcion: "La Ley Federal para la Prevención e Identificación de Operaciones con Recursos de Procedencia Ilícita exige identificar al beneficiario controlador (persona física con ≥25% del capital o control efectivo de la empresa). Su omisión genera 20 pts de riesgo.",
    url: null,
    localData: false,
  },
];

export function ComplianceContext() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Scale className="size-4 text-muted-foreground" />
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Marco legal y regulatorio
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card/40 p-4 space-y-1">
        <p className="text-xs text-muted-foreground leading-relaxed">
          Este reporte evalúa el cumplimiento de la{" "}
          <span className="font-semibold text-foreground">Regla 1.4.14 RGCE 2026</span>
          , que exige a las agencias aduanales realizar diligencia KYB (Know Your Business) antes de inscribir a un cliente en el Padrón de Importadores/Exportadores. Un score &lt;30 permite la inscripción; entre 30 y 69 exige diligencia ampliada; ≥70 bloquea la inscripción.
        </p>
      </div>

      <div className="space-y-2">
        {REGLAS.map((regla) => (
          <details key={regla.titulo} className="group rounded-lg border border-border bg-card">
            <summary className="flex items-center gap-2 cursor-pointer px-4 py-3 text-xs font-medium text-foreground hover:bg-muted/30 transition-colors list-none select-none">
              <BookOpen className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1">{regla.titulo}</span>
              <span className="text-muted-foreground group-open:rotate-90 transition-transform">›</span>
            </summary>
            <div className="px-4 pb-3 pt-0 space-y-2">
              <p className="text-xs text-muted-foreground leading-relaxed">{regla.descripcion}</p>
              {regla.localData && (
                <p className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Database className="size-3 shrink-0" />
                  Los datos de este listado están importados en este sistema y se verifican en tiempo real.
                </p>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
