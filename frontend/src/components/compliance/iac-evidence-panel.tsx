"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileJson, Loader2, ScanSearch, Settings2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { IacEvidenceConfigModal } from "@/components/compliance/iac-evidence-config-modal";
import { api } from "@/lib/api";
import { useAuthStore, type UserRole } from "@/stores/auth-store";

const IAC_CONFIG_EDIT_ROLES: UserRole[] = ["tenant_admin", "security_admin", "platform_admin"];

export function IacEvidencePanel() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = Boolean(user?.role && IAC_CONFIG_EDIT_ROLES.includes(user.role));
  const [configOpen, setConfigOpen] = useState(false);

  const { data, isLoading, refetch, isFetching, isError } = useQuery({
    queryKey: ["iac-evidence", token],
    queryFn: () => api.scanIacEvidence(token!),
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  function downloadReport() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `iac-evidence-${data.generated_at.slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  return (
    <>
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle>Infrastructure evidence</CardTitle>
              <CardDescription>
                Static scan of Helm and OPA deployment manifests for auditor-ready IaC control evidence.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => setConfigOpen(true)}
              >
                <Settings2 className="h-4 w-4" />
                {canEdit ? "Configure" : "View configuration"}
              </Button>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    disabled={isFetching}
                    aria-label="Scan manifests"
                    onClick={() => refetch()}
                  >
                    {isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Scan manifests</TooltipContent>
              </Tooltip>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Scanning deployment manifests…</p>
          ) : isError ? (
            <p className="text-sm text-destructive">Could not run IaC evidence scan.</p>
          ) : !data ? (
            <p className="text-sm text-muted-foreground">Run a scan to generate IaC evidence.</p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{Math.round(data.score)}% posture</Badge>
                <Badge variant="outline">{data.files_scanned} files</Badge>
                <Badge variant="outline">
                  {data.summary.pass} pass · {data.summary.warn} warn · {data.summary.fail} fail
                </Badge>
                {data.scan_paths && data.scan_paths.length > 0 && (
                  <Badge variant="outline">{data.scan_paths.length} paths</Badge>
                )}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="outline" size="icon" className="h-8 w-8" onClick={downloadReport} aria-label="Export JSON">
                      <FileJson className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Export JSON</TooltipContent>
                </Tooltip>
              </div>
              {data.deploy_root && (
                <p className="font-mono text-[10px] text-muted-foreground">Root: {data.deploy_root}</p>
              )}
              <div className="space-y-2">
                {data.checks.map((check) => (
                  <div key={check.id} className="rounded-lg border border-border/60 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{check.title}</span>
                      <Badge
                        variant={
                          check.status === "pass" ? "secondary" : check.status === "warn" ? "warning" : "destructive"
                        }
                      >
                        {check.status}
                      </Badge>
                      <Badge variant="outline">{check.framework}</Badge>
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {check.id}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{check.detail}</p>
                    {check.evidence_files.length > 0 && (
                      <p className="mt-1 text-[10px] text-muted-foreground">
                        Evidence: {check.evidence_files.join(", ")}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <IacEvidenceConfigModal
        open={configOpen}
        token={token}
        canEdit={canEdit}
        onClose={() => setConfigOpen(false)}
        onSaved={() => void refetch()}
      />
    </>
  );
}
