import { type ConsultaSat } from "@/lib/api-client";

const LIST_META: Record<string, { label: string; description: string; url: string }> = {
  art_69: {
    label: "Art. 69 CFF — Contribuyentes con créditos exigibles",
    description:
      "Lista de personas morales con créditos fiscales exigibles no garantizados publicada mensualmente por el SAT.",
    url: "https://www.sat.gob.mx/consultas/76254/consulta-la-lista-del-articulo-69-del-cff",
  },
  art_69b: {
    label: "Art. 69-B CFF — EFOS (Empresas Facturadoras de Operaciones Simuladas)",
    description:
      "Registro de contribuyentes presuntos o definitivos de emitir comprobantes de operaciones inexistentes (EFOS).",
    url: "https://www.sat.gob.mx/consultas/76289/consulta-a-la-lista-del-articulo-69-b-del-cff",
  },
  art_69b_bis: {
    label: "Art. 69-B Bis CFF — Transmisión indebida de pérdidas",
    description:
      "Contribuyentes que han transmitido indebidamente pérdidas fiscales a terceros. Lista de acceso restringido.",
    url: "https://www.sat.gob.mx/consultas/22738/conoce-las-resoluciones-del-articulo-69-b-bis-del-cff",
  },
};

const SUBSTATE_BADGE: Record<string, { label: string; className: string }> = {
  definitivo: { label: "Definitivo", className: "bg-destructive text-background" },
  presunto: { label: "Presunto", className: "bg-destructive/15 text-destructive" },
  desvirtuado: { label: "Desvirtuado", className: "bg-warning/15 text-warning" },
  sentencia_favorable: {
    label: "Sentencia favorable",
    className: "bg-success/15 text-success",
  },
};

type Props = {
  consultas: ConsultaSat[];
};

export function SatEvidenceSection({ consultas }: Props) {
  // Deduplicate: one entry per list_type, keep most recent
  const deduped = Object.values(
    consultas.reduce<Record<string, ConsultaSat>>((acc, c) => {
      const prev = acc[c.list_type];
      if (!prev || new Date(c.consulted_at) > new Date(prev.consulted_at)) {
        acc[c.list_type] = c;
      }
      return acc;
    }, {})
  );

  const consultedCount = deduped.length;
  const foundCount = deduped.filter((c) => c.found).length;

  return (
    <section className="rounded-xl border border-border bg-card p-6 mb-6">
      <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">
        Evidencia — Listas fiscales SAT
      </h2>
      <p className="text-sm text-muted-foreground mb-4">
        Se consultaron{" "}
        <strong className="text-foreground">{consultedCount} listas fiscales</strong> del SAT
        en tiempo real al momento de la evaluación.{" "}
        {foundCount === 0 ? (
          <span className="text-success">Ninguna coincidencia encontrada.</span>
        ) : (
          <span className="text-destructive font-medium">
            {foundCount} coincidencia{foundCount !== 1 ? "s" : ""} detectada
            {foundCount !== 1 ? "s" : ""}.
          </span>
        )}
      </p>

      <div className="space-y-3">
        {deduped.map((c) => {
          const meta = LIST_META[c.list_type];
          const substate = c.match_substate;
          const substadeBadge = substate ? SUBSTATE_BADGE[substate] : null;

          return (
            <div
              key={c.list_type}
              className={`rounded-lg border p-4 ${
                c.found
                  ? "border-destructive/30 bg-destructive/5"
                  : "border-border bg-muted/20"
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-1">
                <p className="text-sm font-medium leading-tight">
                  {meta?.label ?? c.list_type}
                </p>
                <div className="flex items-center gap-2 shrink-0">
                  {substadeBadge && (
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${substadeBadge.className}`}
                    >
                      {substadeBadge.label}
                    </span>
                  )}
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      c.found
                        ? "bg-destructive text-background"
                        : "bg-success/15 text-success"
                    }`}
                  >
                    {c.found ? "Coincidencia" : "Sin coincidencia"}
                  </span>
                </div>
              </div>
              {meta?.description && (
                <p className="text-xs text-muted-foreground mb-2">{meta.description}</p>
              )}
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>RFC consultado: <span className="font-mono">{c.rfc_consultado}</span></span>
                <span>{new Date(c.consulted_at).toLocaleString("es-MX")}</span>
              </div>
              {meta?.url && (
                <a
                  href={meta.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline mt-1.5 block"
                >
                  Verificar en portal SAT ↗
                </a>
              )}
            </div>
          );
        })}

        {deduped.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">
            Sin consultas registradas para este expediente.
          </p>
        )}
      </div>
    </section>
  );
}
