"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, ScanSearch } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiSecurityScanResponse } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

function severityVariant(severity: string): "destructive" | "warning" | "secondary" | "outline" {
  const level = severity.toLowerCase();
  if (level === "critical" || level === "high") return "destructive";
  if (level === "medium") return "warning";
  return "outline";
}

function actionVariant(action: string): "destructive" | "warning" | "success" | "outline" {
  const normalized = action.toLowerCase();
  if (normalized === "block") return "destructive";
  if (normalized === "redact" || normalized === "review") return "warning";
  if (normalized === "allow") return "success";
  return "outline";
}

export function SecurityScanResults({ result }: { result: ApiSecurityScanResponse }) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={result.detected ? "destructive" : "success"}>
          {result.detected ? "Threat detected" : "Clean"}
        </Badge>
        <Badge variant={actionVariant(result.recommended_action)}>{result.recommended_action}</Badge>
        {result.highest_severity && result.highest_severity !== "none" && (
          <Badge variant={severityVariant(result.highest_severity)}>{result.highest_severity}</Badge>
        )}
      </div>
      {result.matches.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {result.matches.map((match) => (
            <li
              key={match.rule_id}
              className="rounded-md border border-border/50 bg-background/40 px-2 py-1.5 text-xs"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{match.name}</span>
                <Badge variant="outline">{match.category}</Badge>
                <Badge variant={severityVariant(match.severity)}>{match.severity}</Badge>
              </div>
              <p className="mt-1 text-muted-foreground">{match.detail}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs text-emerald-400">No threat rules matched server-side inspection.</p>
      )}
    </div>
  );
}

interface SecurityScanPanelProps {
  content: string;
  onContentChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  presets?: { label: string; content: string }[];
  scanLabel?: string;
}

export function SecurityScanPanel({
  content,
  onContentChange,
  placeholder = "Enter content to scan…",
  rows = 5,
  presets = [],
  scanLabel = "Run security scan",
}: SecurityScanPanelProps) {
  const token = useAuthStore((s) => s.token);

  const scanMutation = useMutation({
    mutationFn: () => api.scanSecurityContent(token!, { content }),
  });

  return (
    <div className="space-y-4">
      <textarea
        value={content}
        onChange={(e) => onContentChange(e.target.value)}
        rows={rows}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-ring focus-visible:ring-2"
        placeholder={placeholder}
      />
      {presets.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {presets.map((preset) => (
            <Button key={preset.label} variant="outline" size="sm" onClick={() => onContentChange(preset.content)}>
              {preset.label}
            </Button>
          ))}
        </div>
      )}
      <Button
        onClick={() => scanMutation.mutate()}
        disabled={!token || !content.trim() || scanMutation.isPending}
        className="gap-2"
      >
        {scanMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ScanSearch className="h-4 w-4" />
        )}
        {scanLabel}
      </Button>
      {scanMutation.isError && (
        <p className="text-sm text-destructive">
          {scanMutation.error instanceof Error ? scanMutation.error.message : "Scan failed"}
        </p>
      )}
      {scanMutation.data && <SecurityScanResults result={scanMutation.data} />}
    </div>
  );
}
