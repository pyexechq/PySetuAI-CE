"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function useQAOverview() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["qa-overview", token],
    queryFn: () => api.getQAOverview(token!),
    enabled: Boolean(token),
    staleTime: 15_000,
  });
}

export function useQACycles() {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["qa-cycles", token],
    queryFn: () => api.getQACycles(token!),
    enabled: Boolean(token),
    staleTime: 15_000,
  });
}

export function useQACycle(cycleId: string | null) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["qa-cycle", cycleId, token],
    queryFn: () => api.getQACycle(token!, cycleId!),
    enabled: Boolean(token && cycleId),
    staleTime: 10_000,
  });
}

export function useQADefects(cycleId?: string | null) {
  const token = useAuthStore((s) => s.token);
  return useQuery({
    queryKey: ["qa-defects", cycleId, token],
    queryFn: () => api.getQADefects(token!, cycleId ? { cycle_id: cycleId } : undefined),
    enabled: Boolean(token),
    staleTime: 15_000,
  });
}

export function useQAMutations() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["qa-overview"] });
    queryClient.invalidateQueries({ queryKey: ["qa-cycles"] });
    queryClient.invalidateQueries({ queryKey: ["qa-cycle"] });
    queryClient.invalidateQueries({ queryKey: ["qa-defects"] });
  };

  const createCycle = useMutation({
    mutationFn: (body: { name: string; import_baseline?: boolean; import_baseline_defects?: boolean }) =>
      api.createQACycle(token!, body),
    onSuccess: invalidate,
  });

  const updateCycle = useMutation({
    mutationFn: ({
      cycleId,
      body,
    }: {
      cycleId: string;
      body: { status?: string; release_decision?: string; notes?: string };
    }) => api.updateQACycle(token!, cycleId, body),
    onSuccess: invalidate,
  });

  const updateTestCase = useMutation({
    mutationFn: ({ caseId, status, notes }: { caseId: string; status: string; notes?: string }) =>
      api.updateQATestCase(token!, caseId, { status, notes }),
    onSuccess: invalidate,
  });

  const createDefect = useMutation({
    mutationFn: (body: Parameters<typeof api.createQADefect>[1]) => api.createQADefect(token!, body),
    onSuccess: invalidate,
  });

  const updateDefect = useMutation({
    mutationFn: ({
      defectId,
      body,
    }: {
      defectId: string;
      body: { severity?: string; title?: string; description?: string; status?: string };
    }) => api.updateQADefect(token!, defectId, body),
    onSuccess: invalidate,
  });

  const runAutomated = useMutation({
    mutationFn: ({ cycleId, scope }: { cycleId: string; scope?: "all" | "failed" }) =>
      api.runQAAutomatedTests(token!, cycleId, scope ?? "all"),
    onSuccess: invalidate,
  });

  const fileDefectFromCase = useMutation({
    mutationFn: (caseId: string) => api.fileQADefectFromCase(token!, caseId),
    onSuccess: invalidate,
  });

  return { createCycle, updateCycle, updateTestCase, createDefect, updateDefect, runAutomated, fileDefectFromCase };
}
