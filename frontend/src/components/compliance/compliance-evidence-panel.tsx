"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileJson, Loader2, Save } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApiComplianceSnapshotSummary } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { usePreferencesStore } from "@/stores/preferences-store";
import { formatDateTime } from "@/lib/date-utils";
import { formatNumber } from "@/lib/utils";

import { toast } from "react-hot-toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

function downloadExport(token: string, snapshotId: string, format: "csv" | "json", createdAt: string) {
  const stamp = createdAt.slice(0, 10).replace(/-/g, "");
  const url = `${API_BASE}/compliance/snapshots/${snapshotId}/export?format=${format}`;
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then((res) => {
      if (!res.ok) throw new Error("Export failed");
      return res.blob();
    })
    .then((blob) => {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `compliance-evidence-${stamp}.${format}`;
      link.click();
      URL.revokeObjectURL(link.href);
    })
    .catch(() => {
      toast.error("Unable to download evidence export.");
    });
}

export function ComplianceEvidencePanel() {
  const token = useAuthStore((s) => s.token);
  const timezone = usePreferencesStore((s) => s.timezone);
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState("");

  const { data: snapshots = [], isLoading } = useQuery({
    queryKey: ["compliance-snapshots", token],
    queryFn: () => api.listComplianceSnapshots(token!),
    enabled: Boolean(token),
  });

  const saveMutation = useMutation({
    mutationFn: () => api.createComplianceSnapshot(token!, { notes: notes.trim() }),
    onSuccess: () => {
      setNotes("");
      queryClient.invalidateQueries({ queryKey: ["compliance-snapshots"] });
    },
  });

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle>Evidence Snapshots</CardTitle>
        <CardDescription>
          Save point-in-time compliance posture with control-level evidence for auditors and report attachments.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="snapshot-notes" className="text-sm font-medium">
            Notes (optional)
          </label>
          <textarea
            id="snapshot-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="e.g. Q3 audit baseline before HIPAA review"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-ring focus-visible:ring-2"
          />
          <Button
            onClick={() => saveMutation.mutate()}
            disabled={!token || saveMutation.isPending}
            className="gap-2"
          >
            {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save evidence snapshot
          </Button>
        </div>

        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading snapshots…</p>
        ) : snapshots.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border/70 p-6 text-center text-sm text-muted-foreground">
            No snapshots yet. Save the current framework scores and control evidence for export.
          </p>
        ) : (
          <div className="space-y-2">
            {snapshots.map((snapshot: ApiComplianceSnapshotSummary) => (
              <div
                key={snapshot.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 p-3"
              >
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium">
                      {formatDateTime(snapshot.created_at, timezone)}
                    </p>
                    <Badge variant="secondary">{Math.round(snapshot.overall_score)}% overall</Badge>
                    <Badge variant="outline">
                      {snapshot.frameworks_compliant}/{snapshot.frameworks_total} compliant
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    By {snapshot.created_by_name || "—"} · {formatNumber(snapshot.frameworks_total)} frameworks
                    tracked
                  </p>
                  {snapshot.notes && <p className="text-xs text-muted-foreground">{snapshot.notes}</p>}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1"
                    onClick={() => token && downloadExport(token, snapshot.id, "csv", snapshot.created_at)}
                  >
                    <Download className="h-3.5 w-3.5" />
                    CSV
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1"
                    onClick={() => token && downloadExport(token, snapshot.id, "json", snapshot.created_at)}
                  >
                    <FileJson className="h-3.5 w-3.5" />
                    JSON
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
