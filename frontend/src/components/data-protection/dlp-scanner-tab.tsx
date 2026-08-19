"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Copy, ScanSearch } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { toast } from "react-hot-toast";

const SAMPLE_TEXT =
  "Please update the billing record for John Doe, SSN 123-45-6789, email john.doe@example.com. Bank account routing number 026009593.";

const MAX_CONTENT_LENGTH = 32000;

function sensitivityBadgeVariant(label: string): "destructive" | "warning" | "secondary" | "outline" {
  if (label.startsWith("RESTRICTED_")) return "destructive";
  if (label === "CONFIDENTIAL_FINANCIAL") return "warning";
  if (label === "INTERNAL_PII") return "secondary";
  return "outline";
}

export function DlpScannerTab({ token }: { token: string | null }) {
  const [content, setContent] = useState(SAMPLE_TEXT);

  const scanMutation = useMutation({
    mutationFn: () => api.scanDataProtectionContent(token!, { content }),
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.message : "Unable to scan content."),
  });

  const result = scanMutation.data;

  function handleCopyRedacted() {
    if (!result?.redacted_content) return;
    void navigator.clipboard.writeText(result.redacted_content);
    toast.success("Redacted content copied.");
  }

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ScanSearch className="h-5 w-5" />
          DLP scanner
        </CardTitle>
        <CardDescription>
          Test the live DLP engine against sample text — see detected entities, sensitivity labels, and a redacted preview.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium">Content to scan</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value.slice(0, MAX_CONTENT_LENGTH))}
            rows={6}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
          />
          <p className="text-xs text-muted-foreground">{content.length}/{MAX_CONTENT_LENGTH} characters</p>
        </div>

        <Button
          className="gap-2"
          disabled={!token || !content.trim() || scanMutation.isPending}
          onClick={() => scanMutation.mutate()}
        >
          <ScanSearch className="h-4 w-4" />
          {scanMutation.isPending ? "Scanning…" : "Scan content"}
        </Button>

        {result && (
          <div className="space-y-4 rounded-lg border border-border/60 p-4">
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className="text-muted-foreground">Region: {result.region}</span>
              <span className="text-muted-foreground">Matches: {result.match_count}</span>
              {result.highest_sensitivity && (
                <Badge variant={sensitivityBadgeVariant(result.highest_sensitivity)}>
                  Highest: {result.highest_sensitivity}
                </Badge>
              )}
              {!result.has_pii && <Badge variant="success">No PII detected</Badge>}
            </div>

            {result.classifications.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-sm font-medium">Entities detected</p>
                <div className="flex flex-wrap gap-1.5">
                  {result.classifications.map((entity) => (
                    <Badge key={entity} variant="outline">
                      {entity}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {result.sensitivity_labels.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-sm font-medium">Sensitivity labels</p>
                <div className="flex flex-wrap gap-1.5">
                  {result.sensitivity_labels.map((label) => (
                    <Badge key={label} variant={sensitivityBadgeVariant(label)}>
                      {label}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {result.redacted_content && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Redacted preview</p>
                  <Button variant="outline" size="sm" className="gap-1.5" onClick={handleCopyRedacted}>
                    <Copy className="h-3.5 w-3.5" />
                    Copy
                  </Button>
                </div>
                <pre className="whitespace-pre-wrap rounded-md border border-border/60 bg-muted/20 p-3 text-xs font-mono">
                  {result.redacted_content}
                </pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
