"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { CreateJobPayload } from "@/lib/types";

export function useGenerateVideo() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (payload: CreateJobPayload) => api.createJob(payload),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      router.push(`/jobs/${job.id}`);
    },
  });
}
