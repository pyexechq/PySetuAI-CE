"use client";

import { useState, type ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Trash2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatNumber } from "@/lib/utils";

export function RequestLogSettingsCard() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["request-log-settings", token],
    queryFn: () => api.getRequestLogSettings(token!),
    enabled: Boolean(token),
  });
  const [retention, setRetention] = useState<string>("");

  const saveMutation = useMutation({
    mutationFn: (days: number) => api.updateRequestLogSettings(token!, days),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["request-log-settings"] }),
  });

  const purgeMutation = useMutation({
    mutationFn: () => api.purgeRequestLogs(token!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["request-log-settings"] }),
  });

  const retentionValue = retention || String(data?.retention_days ?? 30);

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Database className="h-4 w-4 text-sky-400" />
          Request log retention
        </CardTitle>
        <CardDescription>
          Full gateway request/response bodies are stored for audit replay. Purge removes entries older than retention.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Retention (days)</label>
          <input
            type="number"
            min={1}
            max={365}
            value={retentionValue}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setRetention(e.target.value)}
            className="flex h-9 w-28 rounded-md border border-input bg-background px-3 text-sm outline-none ring-ring focus-visible:ring-2"
          />
        </div>
        <Button
          size="sm"
          disabled={saveMutation.isPending}
          onClick={() => saveMutation.mutate(Number(retentionValue))}
        >
          Save
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          disabled={purgeMutation.isPending}
          onClick={() => purgeMutation.mutate()}
        >
          <Trash2 className="h-3.5 w-3.5" />
          Purge expired
        </Button>
        {data && (
          <p className="text-sm text-muted-foreground">
            {formatNumber(data.stored_entries)} stored entries
            {purgeMutation.data?.purged ? ` · purged ${purgeMutation.data.purged}` : ""}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
