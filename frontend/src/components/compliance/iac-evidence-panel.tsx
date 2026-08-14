"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileJson, Loader2, ScanSearch } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function IacEvidencePanel() {
  const token = useAuthStore((s) => s.token);

  const { data, isLoading, refetch, isFetching } = useQuery({
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
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle>Infrastructure evidence</CardTitle>
            <CardDescription>
              Static scan of Helm and OPA deployment manifests for auditor-ready IaC control evidence.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" className="gap-2" disabled={isFetching} onClick={() => refetch()}>
            {isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
            Scan manifests
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Scanning deployment manifests…</p>
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
              <Button variant="outline" size="sm" className="gap-1" onClick={downloadReport}>
                <FileJson className="h-3.5 w-3.5" />
                Export JSON
                <Download className="h-3.5 w-3.5 opacity-60" />
              </Button>
            </div>
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
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{check.detail}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
