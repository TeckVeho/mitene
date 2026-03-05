"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { CreateAudioJobPayload } from "@/lib/types";

export function useGenerateAudio() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (payload: CreateAudioJobPayload) => api.createAudioJob(payload),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      router.push(`/jobs/${job.id}`);
    },
  });
}
