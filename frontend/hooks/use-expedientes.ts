import useSWR, { mutate } from "swr";
import { api, type Expediente } from "@/lib/api-client";

export const EXPEDIENTES_KEY = "/expedientes";

const fetcher = () => api.listExpedientes();

export function useExpedientes(fallbackData?: Expediente[]) {
  return useSWR(EXPEDIENTES_KEY, fetcher, {
    fallbackData,
    revalidateOnFocus: true,
    dedupingInterval: 2000,
  });
}

export function revalidateExpedientes() {
  return mutate(EXPEDIENTES_KEY);
}
