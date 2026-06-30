const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
// El trailing slash de NEXT_PUBLIC_API_URL + el leading slash de cada path
// produce URL con // (ej: vercel.app//expedientes), que Vercel redirige y
// ese redirect rompe el preflight CORS. Normalizar a un solo slash.
const API_URL = RAW_API_URL.replace(/\/+$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
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
  extraction_status:
    | "pending"
    | "processing"
    | "extracted"
    | "human_reviewed"
    | "not_applicable"
    | "error";
  fields: Record<string, unknown>;
  human_reviewed: boolean;
  storage_path?: string | null;
};

export type FactorDetail = {
  factor_code: string;
  points: number;
  is_critical_block: boolean;
  detail: string;
  evidence: Record<string, unknown> | null;
  legal_ref: string;
  category: "sat" | "discrepancia" | "completitud" | "otro";
};

export type EvaluationResult = {
  decision: Decision;
  score_total: number;
  factores_score: Record<string, number>;
  factores_detail: FactorDetail[];
  factores_informativos?: FactorDetail[];
  acciones_sugeridas: string[];
  evaluated_at: string;
};

export type ClassifyResult = {
  doc_type: string;
  confidence: "high" | "low";
  suggested_label: string;
};

export type UploadDocumentoResult = {
  documento_id: string;
  extraction_status: string;
  needs_review: boolean;
  fields?: Record<string, unknown>;
};

export type ConsultaSat = {
  id: string;
  expediente_id: string;
  list_type: string;
  rfc_consultado: string;
  found: boolean;
  match_substate: string | null;
  match_detail: Record<string, unknown> | null;
  consulted_at: string;
  import_run_id: string | null;
  source_url: string | null;
};

export type EvaluationHistoryEntry = {
  id: string;
  score_total: number;
  decision: Decision;
  critical_blocks: string[];
  created_at: string;
};

export class DuplicateDocumentoError extends Error {
  constructor(public readonly documentoId: string) {
    super("Documento duplicado");
  }
}

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

  updateExpediente: (
    id: string,
    data: {
      razon_social?: string;
      rfc?: string;
      domicilio_fiscal?: string;
      representante_legal?: string;
    }
  ): Promise<Expediente> =>
    request(`/expedientes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteExpediente: (id: string): Promise<void> =>
    request(`/expedientes/${id}`, { method: "DELETE" }),

  evaluate: (id: string): Promise<EvaluationResult> =>
    request(`/expedientes/${id}/evaluate`, { method: "POST" }),

  getLatestEvaluation: (id: string): Promise<EvaluationResult | null> =>
    request(`/expedientes/${id}/evaluations/latest`),

  listEvaluations: (expedienteId: string): Promise<EvaluationHistoryEntry[]> =>
    request(`/expedientes/${expedienteId}/evaluations`),

  listDocumentos: (expedienteId: string): Promise<Documento[]> =>
    request(`/documentos?expediente_id=${expedienteId}`),

  getDocumento: async (
    expedienteId: string,
    documentoId: string
  ): Promise<Documento | null> => {
    const docs = await request<Documento[]>(
      `/documentos?expediente_id=${expedienteId}`
    );
    return docs.find((d) => d.id === documentoId) ?? null;
  },

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

  uploadDocumento: async (
    expedienteId: string,
    docType: string,
    file: File
  ): Promise<UploadDocumentoResult> => {
    const form = new FormData();
    form.append("expediente_id", expedienteId);
    form.append("doc_type", docType);
    form.append("file", file);
    const res = await fetch(`${API_URL}/documentos/upload`, {
      method: "POST",
      body: form,
    });
    if (res.status === 409) {
      const data = await res.json();
      throw new DuplicateDocumentoError(data.detail?.documento_id ?? "");
    }
    if (!res.ok) throw new Error(`Upload error ${res.status}: ${await res.text()}`);
    return res.json();
  },

  classifyDocumento: async (file: File): Promise<ClassifyResult> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/documentos/classify`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`Classify error ${res.status}`);
    return res.json();
  },

  reportChange: (id: string, reason: string): Promise<void> =>
    request(`/expedientes/${id}/report-change`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  listConsultasSat: (expedienteId: string): Promise<ConsultaSat[]> =>
    request(`/expedientes/${expedienteId}/consultas-sat`),

  deleteDocumento: (id: string): Promise<void> =>
    request(`/documentos/${id}`, { method: "DELETE" }),
};

// Backward compat for existing page.tsx
export async function checkHealth(): Promise<{ status: string }> {
  return api.checkHealth();
}
