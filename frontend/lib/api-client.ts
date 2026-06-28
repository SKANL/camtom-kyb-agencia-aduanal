const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
// El trailing slash de NEXT_PUBLIC_API_URL + el leading slash de cada path
// produce URL con // (ej: vercel.app//expedientes), que Vercel redirige y
// ese redirect rompe el preflight CORS. Normalizar a un solo slash.
const API_URL = RAW_API_URL.replace(/\/+$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export type Decision = "safe" | "review_required" | "high_risk";

export type Expediente = {
  id: string;
  razon_social: string;
  rfc: string;
  status: string;
  decision: Decision | null;
  score_total: number | null;
  domicilio_fiscal?: string;
  representante_legal?: string;
};

export type Documento = {
  id: string;
  expediente_id: string;
  doc_type: string;
  entry_method: "uploaded" | "manual";
  extraction_status: "pending" | "processing" | "done" | "error";
  fields: Record<string, unknown>;
  human_reviewed: boolean;
};

export type EvaluationResult = {
  decision: Decision;
  score_total: number;
  factores_score: Record<string, number>;
  acciones_sugeridas: string[];
  evaluated_at: string;
};

export type SatImportRun = {
  id: string;
  list_type: string;
  status: string;
  rows_imported: number | null;
  started_at: string;
  finished_at: string | null;
};

export const api = {
  checkHealth: (): Promise<{ status: string }> =>
    request("/health"),

  listExpedientes: (): Promise<Expediente[]> =>
    request("/expedientes"),

  getExpediente: (id: string): Promise<Expediente> =>
    request(`/expedientes/${id}`),

  createExpediente: (data: {
    razon_social: string;
    rfc: string;
    domicilio_fiscal?: string;
    representante_legal?: string;
  }): Promise<Expediente> =>
    request("/expedientes", { method: "POST", body: JSON.stringify(data) }),

  evaluate: (id: string): Promise<EvaluationResult> =>
    request(`/expedientes/${id}/evaluate`, { method: "POST" }),

  getLatestEvaluation: (id: string): Promise<EvaluationResult | null> =>
    request(`/expedientes/${id}/evaluations/latest`),

  listDocumentos: (expedienteId: string): Promise<Documento[]> =>
    request(`/documentos?expediente_id=${expedienteId}`),

  crearDocumento: (
    expedienteId: string,
    docType: string,
    entryMethod: "uploaded" | "manual"
  ): Promise<{ documento_id: string; signed_url?: string }> =>
    request("/documentos", {
      method: "POST",
      body: JSON.stringify({
        expediente_id: expedienteId,
        doc_type: docType,
        entry_method: entryMethod,
      }),
    }),

  extractDocumento: (documentoId: string): Promise<Documento> =>
    request(`/documentos/${documentoId}/extract`, { method: "POST" }),

  reviewDocumento: (
    id: string,
    fields: Record<string, unknown>
  ): Promise<Documento> =>
    request(`/documentos/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ fields }),
    }),

  reportChange: (id: string, reason: string): Promise<void> =>
    request(`/expedientes/${id}/report-change`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  // Admin
  triggerSatImport: (listType: string): Promise<SatImportRun> =>
    request(`/admin/ingest/${listType}`, { method: "POST" }),

  listSatImportRuns: (): Promise<SatImportRun[]> =>
    request("/admin/sat-import-runs"),

  listConsultasSat: (expedienteId: string): Promise<unknown[]> =>
    request(`/expedientes/${expedienteId}/consultas-sat`),
};

// Backward compat for existing page.tsx
export async function checkHealth(): Promise<{ status: string }> {
  return api.checkHealth();
}
