"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileJson, Loader2, Lock, Route, Settings2, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { QuickLinkPills } from "@/components/shared/section-chrome";
import { DataMovementPolicyModal } from "@/components/compliance/data-movement-policy-modal";
import { type ApiGenaiEvidenceSummary } from "@/lib/api";
import { api } from "@/lib/api";
import { useAuthStore, type UserRole } from "@/stores/auth-store";
import { usePreferencesStore } from "@/stores/preferences-store";
import { formatDateTime } from "@/lib/date-utils";
import { toast } from "react-hot-toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";
const POLICY_EDIT_ROLES: UserRole[] = ["tenant_admin", "security_admin", "platform_admin"];

const CONFIG_LINKS = [
  { href: "/ai-gateway?tab=rag", label: "Governed RAG", icon: Route },
  { href: "/data-protection", label: "DLP & classification", icon: Lock },
  { href: "/settings/integrations", label: "Vector store", icon: Settings2 },
  { href: "/compliance?tab=exemptions", label: "Break-glass", icon: ShieldAlert },
] as const;

function downloadGenaiEvidence(token: string, bundleId: string, createdAt: string) {
  const stamp = createdAt.slice(0, 10).replace(/-/g, "");
  const url = `${API_BASE}/rag-gateway/evidence/${bundleId}/export`;
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then((res) => {
      if (!res.ok) throw new Error("Export failed");
      return res.blob();
    })
    .then((blob) => {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `genai-evidence-${stamp}-${bundleId.slice(0, 8)}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
    })
    .catch(() => {
      toast.error("Unable to download GenAI evidence bundle.");
    });
}

function statusBadge(bundle: ApiGenaiEvidenceSummary) {
  if (bundle.allowed) {
    return (
      <Badge variant="secondary" className="gap-1 text-emerald-400">
        <ShieldCheck className="h-3 w-3" />
        Allowed
      </Badge>
    );
  }
  return (
    <Badge variant="destructive" className="gap-1">
      <ShieldAlert className="h-3 w-3" />
      Blocked
    </Badge>
  );
}

export function GenaiEvidencePanel() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const timezone = usePreferencesStore((s) => s.timezone);
  const queryClient = useQueryClient();
  const canEditPolicy = Boolean(user?.role && POLICY_EDIT_ROLES.includes(user.role));
  const canSeed = user?.role === "tenant_admin" || user?.role === "security_admin";
  const [policyOpen, setPolicyOpen] = useState(false);

  const { data: bundles = [], isLoading } = useQuery({
    queryKey: ["genai-evidence", token],
    queryFn: () => api.listGenaiEvidenceBundles(token!),
    enabled: Boolean(token),
  });

  const seedMutation = useMutation({
    mutationFn: () => api.createDemoRagEvents(token!),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["genai-evidence"] });
      queryClient.invalidateQueries({ queryKey: ["audit-logs"] });
      toast.success(result.message);
    },
    onError: () => toast.error("Unable to create demo RAG events."),
  });

  return (
    <>
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <CardTitle>GenAI DLP Evidence</CardTitle>
              <CardDescription>
                Governed RAG and data-movement decisions with classification, OPA policy outcomes, and control mappings for auditors.
                Evidence bundles are generated automatically when governed ingest runs.
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setPolicyOpen(true)}>
              <Settings2 className="h-4 w-4" />
              {canEditPolicy ? "Data-movement policy" : "View policy"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <QuickLinkPills links={CONFIG_LINKS} />
          {canSeed && (
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              disabled={!token || seedMutation.isPending}
              onClick={() => seedMutation.mutate()}
            >
              {seedMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Load demo RAG events
            </Button>
          )}
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading GenAI evidence bundles…</p>
          ) : bundles.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border/70 p-6 text-center text-sm text-muted-foreground">
              No GenAI evidence yet. Use &quot;Load demo RAG events&quot; or run a governed ingest from AI Gateway → Governed RAG.
            </p>
          ) : (
            <div className="space-y-2">
              {bundles.map((bundle) => (
                <div
                  key={bundle.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 p-3"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium">{formatDateTime(bundle.created_at, timezone)}</p>
                      {statusBadge(bundle)}
                      <Badge variant="outline">{bundle.bundle_type.replace(/_/g, " ")}</Badge>
                      {bundle.highest_sensitivity && (
                        <Badge variant="outline">{bundle.highest_sensitivity}</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      By {bundle.actor || "—"}
                      {bundle.destination ? ` · destination: ${bundle.destination}` : ""}
                      {bundle.blocked_hop ? ` · blocked at ${bundle.blocked_hop}` : ""}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1"
                    onClick={() => token && downloadGenaiEvidence(token, bundle.id, bundle.created_at)}
                  >
                    <FileJson className="h-3.5 w-3.5" />
                    JSON
                    <Download className="h-3.5 w-3.5 opacity-60" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <DataMovementPolicyModal
        open={policyOpen}
        token={token}
        canEdit={canEditPolicy}
        onClose={() => setPolicyOpen(false)}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ["genai-evidence"] })}
      />
    </>
  );
}
