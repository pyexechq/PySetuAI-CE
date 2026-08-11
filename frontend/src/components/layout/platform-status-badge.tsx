"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api, type ApiGatewayStatus } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

type HealthState = {
  label: "Live" | "Issue";
  variant: "success" | "destructive";
  detail: string;
};

function evaluateGatewayHealth(status: ApiGatewayStatus | undefined, failed: boolean): HealthState {
  if (failed || !status) {
    return {
      label: "Issue",
      variant: "destructive",
      detail: "Unable to reach the HelixGuard control plane. Check network or backend services.",
    };
  }

  const issues: string[] = [];

  if (status.status !== "operational") {
    issues.push(`Gateway status is ${status.status}`);
  }
  if (status.proxy_mode === "none") {
    issues.push("AI upstream is not configured");
  }
  if (status.opa_enabled && !status.opa_available) {
    issues.push("OPA policy engine is unavailable");
  }

  if (issues.length > 0) {
    return {
      label: "Issue",
      variant: "destructive",
      detail: issues.join(" · "),
    };
  }

  return {
    label: "Live",
    variant: "success",
    detail: "Gateway operational and upstream connected.",
  };
}

export function PlatformStatusBadge() {
  const token = useAuthStore((s) => s.token);

  const { data, isError, isLoading } = useQuery({
    queryKey: ["platform-status", token],
    queryFn: () => api.getGatewayStatus(token!),
    enabled: Boolean(token),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  if (!token) {
    return null;
  }

  const health = evaluateGatewayHealth(data, isError);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant={health.variant}
          className={cn(
            "hidden gap-1.5 sm:inline-flex",
            isLoading && "opacity-70"
          )}
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              health.variant === "success" ? "bg-emerald-400" : "bg-red-400",
              health.label === "Live" && "animate-pulse"
            )}
            aria-hidden
          />
          {isLoading ? "Checking…" : health.label}
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs">
        {isLoading ? "Checking platform health…" : health.detail}
      </TooltipContent>
    </Tooltip>
  );
}
