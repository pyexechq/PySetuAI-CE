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
      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-amber-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2.5 max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                Human-in-the-Loop Gate
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                Four-Eyes Access Control
              </Badge>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              Approvals & Break-Glass Authorizations
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Review and authorize sensitive autonomous agent tool executions, high-risk MCP operations, and emergency break-glass policy overrides.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 gap-3 shrink-0">
            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Pending Action</span>
                <ShieldCheck className="h-3.5 w-3.5 text-amber-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-amber-600 dark:text-amber-400">{pendingCount}</p>
              <p className="text-[10px] text-muted-foreground">Requires sign-off</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Total Requests</span>
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{approvals.length}</p>
              <p className="text-[10px] text-muted-foreground">Historical records</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
          {(["pending", "all"] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setStatusFilter(filter)}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                statusFilter === filter
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {filter === "pending" ? `Pending (${pendingCount})` : `All Records (${approvals.length})`}
            </button>
          ))}
        </div>
      </div>

      {approvals.length === 0 ? (
        <Card className="border-border bg-card shadow-sm rounded-2xl">
          <CardContent className="p-12 text-center">
            <ShieldCheck className="mx-auto h-10 w-10 text-muted-foreground/40 mb-2" />
            <p className="font-semibold text-base">No approval requests</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Agent actions and MCP tool access requests requiring human sign-off will appear here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {approvals.map((approval: ApiApprovalRequest) => (
            <div
              key={approval.id}
              className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 shadow-sm md:flex-row md:items-center md:justify-between hover:border-primary/50 hover:shadow-md transition-all"
            >
              <div className="min-w-0 flex-1 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-primary bg-primary/10 px-2.5 py-1 rounded-lg border border-primary/20">
                    {approval.resource || approval.action}
                  </span>
                  <Badge variant={approval.status === "pending" ? "warning" : approval.status === "approved" ? "success" : "secondary"}>
                    {approval.status}
                  </Badge>
                  <Badge variant={riskVariant(approval.risk_score)}>risk {approval.risk_score}</Badge>
                </div>

                <div>
                  <p className="text-sm font-semibold text-foreground">
                    {approval.user_name || "unknown user"}
                    {approval.tool ? <span className="text-primary font-bold"> · {approval.tool}</span> : ""} 
                    <span className="text-muted-foreground font-normal"> ({approval.action})</span>
                  </p>

                  {approval.action === "mcp_access_request" && (
                    <div className="mt-2 space-y-1 bg-muted/40 p-3 rounded-xl border border-border/50 text-xs">
                      {approval.requested_mcp_tools && approval.requested_mcp_tools.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                          <span className="font-semibold text-foreground">Requested Tools:</span>
                          {approval.requested_mcp_tools.map((t: string) => (
                            <span key={t} className="font-mono text-[11px] bg-background border border-border px-2 py-0.5 rounded-md font-medium text-foreground">
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                      {approval.reason && (
                        <p className="text-muted-foreground leading-relaxed">
                          <span className="font-semibold text-foreground">Justification:</span> {approval.reason}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {(approval.classification ?? []).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {approval.classification!.map((label, index) => (
                      <Badge key={`${approval.id}-${index}`} variant="outline" className="text-xs">
                        {label}
                      </Badge>
                    ))}
                  </div>
                )}
                {approval.policy_name && (
                  <p className="text-xs text-muted-foreground">Policy: {approval.policy_name}</p>
                )}
              </div>

              <div className="flex shrink-0 items-center gap-2">
                {approval.status === "pending" ? (
                  <>
                    <Button
                      size="sm"
                      className="gap-1.5 rounded-xl font-bold text-xs shadow-xs"
                      disabled={decide.isPending}
                      onClick={() => decide.mutate({ id: approval.id, approve: true })}
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1.5 rounded-xl font-bold text-xs border-border"
                      disabled={decide.isPending}
                      onClick={() => decide.mutate({ id: approval.id, approve: false })}
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      Reject
                    </Button>
                  </>
                ) : (
                  <div className="text-right">
                    <p className="text-xs font-semibold text-foreground capitalize">
                      {approval.status} by {approval.decided_by || "admin"}
                    </p>
                    {approval.decided_at && (
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {new Date(approval.decided_at).toLocaleString()}
                      </p>
                    )}
                  </div>
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
