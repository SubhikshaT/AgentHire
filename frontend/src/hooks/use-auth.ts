"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { api, ApiError } from "@/lib/api";
import type { Role, User } from "@/types/auth";

export const ME_KEY = ["auth", "me"] as const;

export function homePathFor(role: Role) {
  return role === "recruiter" ? "/dashboard" : "/candidate/home";
}

export function useMe() {
  return useQuery<User | null>({
    queryKey: ME_KEY,
    queryFn: async () => {
      try {
        return await api<User>("/auth/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: 60_000,
    retry: false,
  });
}

export type LoginInput = { email: string; password: string };
export type RegisterInput = LoginInput & { name: string; role: Role };

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LoginInput) =>
      api<User>("/auth/login", { method: "POST", body: data }),
    onSuccess: (user) => qc.setQueryData(ME_KEY, user),
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RegisterInput) =>
      api<User>("/auth/register", { method: "POST", body: data }),
    onSuccess: (user) => qc.setQueryData(ME_KEY, user),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSettled: () => {
      qc.clear();
      qc.setQueryData(ME_KEY, null);
      router.replace("/login");
    },
  });
}
