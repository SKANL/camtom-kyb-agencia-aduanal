"use client";
import useSWR from "swr";
import { api } from "@/lib/api-client";
import type { Expediente, Documento, EvaluationResult } from "@/lib/api-client";

export function useExpediente(id: string) {
  const { data, isLoading, mutate, error } = useSWR<Expediente>(
    id ? `expediente-${id}` : null,
    () => api.getExpediente(id),
    { revalidateOnFocus: true }
  );
  return { expediente: data ?? null, isLoading, mutate, error };
}

export function useDocumentos(expedienteId: string) {
  const { data, isLoading, mutate, error } = useSWR<Documento[]>(
    expedienteId ? `documentos-${expedienteId}` : null,
    () => api.listDocumentos(expedienteId),
    { revalidateOnFocus: true }
  );
  return { documentos: data ?? [], isLoading, mutate, error };
}

export function useLatestEvaluation(expedienteId: string) {
  const { data, isLoading, mutate, error } = useSWR<EvaluationResult | null>(
    expedienteId ? `evaluation-latest-${expedienteId}` : null,
    () => api.getLatestEvaluation(expedienteId),
    { revalidateOnFocus: true }
  );
  return { evaluation: data ?? null, isLoading, mutate, error };
}
