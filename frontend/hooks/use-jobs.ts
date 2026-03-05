"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useJobStats() {
  return useQuery({
    queryKey: ["jobs", "stats"],
    queryFn: () => api.getStats(),
    refetchInterval: 10000,
  });
}

export function useJobs(status?: string, type?: string) {
  return useQuery({
    queryKey: ["jobs", status ?? "all", type ?? "all"],
    queryFn: () => api.getJobs(status, type),
    refetchInterval: 10000,
  });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ["jobs", id],
    queryFn: () => api.getJob(id),
    refetchInterval: (query) => {
      const job = query.state.data;
      if (job?.status === "processing" || job?.status === "pending") return 5000;
      return false;
    },
    enabled: !!id,
  });
}
