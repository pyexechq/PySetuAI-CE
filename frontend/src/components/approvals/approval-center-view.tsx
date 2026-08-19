"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, ShieldCheck, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiApprovalRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

function riskVariant(score: number): "default" | "secondary" | "warning" | "destructive" | "success" | "outline" {
  if (score >= 80) return "destructive";
  if (score >= 60) return "warning";
  if (score >= 30) return "secondary";
  return "success";
}

function ApprovalCenterViewInner() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<"pending" | "all">("pending");

  const { data: approvals = [], isLoading } = useQuery({
    queryKey: ["approvals", token, statusFilter],
    queryFn: () => api.getApprovals(token!, statusFilter),
    enabled: Boolean(token),
  });

  const decide = useMutation({
    mutationFn: ({ id, approve, reason }: { id: string; approve: boolean; reason?: string }) =>
      approve ? api.approveApproval(token!, id, reason) : api.rejectApproval(token!, id, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["approvals"] }),
  });

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card/50">
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading approvals…
        </CardContent>
      </Card>
    );
  }

  const pendingCount = approvals.filter((approval) => approval.status === "pending").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge variant="warning">Pending: {pendingCount}</Badge>
          <Badge variant="outline">Total shown: {approvals.length}</Badge>
        </div>
        <div className="flex items-center gap-2">
          {(["pending", "all"] as const).map((filter) => (
            <Button
              key={filter}
              variant={statusFilter === filter ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setStatusFilter(filter)}
            >
              {filter[0].toUpperCase() + filter.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {approvals.length === 0 ? (
        <Card className="border-border/60 bg-card/50">
          <CardContent className="p-8 text-center">
            <ShieldCheck className="mx-auto h-8 w-8 text-muted-foreground/50" />
            <p className="mt-3 font-medium">No approval requests</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Agent actions requiring approval will appear here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {approvals.map((approval: ApiApprovalRequest) => (
            <div
              key={approval.id}
              className="flex flex-col gap-4 rounded-xl border border-border/60 bg-background/50 p-4 md:flex-row md:items-center md:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-mono text-sm font-medium">{approval.resource || approval.action}</p>
                  <Badge variant={approval.status === "pending" ? "warning" : approval.status === "approved" ? "success" : "secondary"}>
                    {approval.status}
                  </Badge>
                  <Badge variant={riskVariant(approval.risk_score)}>risk {approval.risk_score}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {approval.user_name || "unknown user"}
                  {approval.tool ? ` · ${approval.tool}` : ""} · {approval.action}
                </p>
                {(approval.classification ?? []).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {approval.classification!.map((label, index) => (
                      <Badge key={`${approval.id}-${index}`} variant="outline" className="text-xs">
                        {label}
                      </Badge>
                    ))}
                  </div>
                )}
                {approval.policy_name && (
                  <p className="mt-1 text-xs text-muted-foreground">Policy: {approval.policy_name}</p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {approval.status === "pending" ? (
                  <>
                    <Button
                      size="sm"
                      className="gap-1"
                      disabled={decide.isPending}
                      onClick={() => decide.mutate({ id: approval.id, approve: true })}
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1"
                      disabled={decide.isPending}
                      onClick={() => decide.mutate({ id: approval.id, approve: false })}
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      Reject
                    </Button>
                  </>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    {approval.decided_by || "system"}
                    {approval.decided_at ? ` · ${new Date(approval.decided_at).toLocaleString()}` : ""}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ApprovalCenterView() {
  return <ApprovalCenterViewInner />;
}
