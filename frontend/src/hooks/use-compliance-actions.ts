"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function useComplianceActions() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
    queryClient.invalidateQueries({ queryKey: ["compliance-frameworks"] });
  };

  const reevaluateFramework = useMutation({
    mutationFn: (frameworkKey: string) => api.reevaluateComplianceFramework(token!, frameworkKey),
    onSuccess: invalidate,
  });

  const generateRemediation = useMutation({
    mutationFn: (body: { framework_name: string; control_id: string; mode: "manual" | "ai" }) =>
      api.generateComplianceRemediation(token!, body),
  });

  return { reevaluateFramework, generateRemediation };
}
