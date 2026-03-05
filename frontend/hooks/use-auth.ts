"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useAuthStatus() {
  return useQuery({
    queryKey: ["auth-status"],
    queryFn: () => api.getAuthStatus(),
    refetchInterval: 30_000,
    staleTime: 25_000,
  });
}

export function useTriggerLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.triggerLogin(),
    onSuccess: () => {
      // ログイン完了をポーリングで検知するため、定期的に再フェッチ
      const interval = setInterval(async () => {
        await queryClient.invalidateQueries({ queryKey: ["auth-status"] });
        const data = queryClient.getQueryData<{ status: string }>(["auth-status"]);
        if (data?.status === "authenticated") {
          clearInterval(interval);
        }
      }, 5_000);

      // 最大2分後に自動停止
      setTimeout(() => clearInterval(interval), 120_000);
    },
  });
}
