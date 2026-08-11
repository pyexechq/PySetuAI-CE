"use client";

import dynamic from "next/dynamic";
import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { GridApi } from "ag-grid-community";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuditLogs } from "@/hooks/use-audit-logs";
import type { AuditLogEntry } from "@/lib/types/domain";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatDateRangeLabel } from "@/lib/date-range";
import { useDateRangeStore } from "@/stores/date-range-store";
import { Download, Pause, Play, Radio, Search, Filter } from "lucide-react";
import { SiemConnectorsPanel } from "@/components/audit-explorer/siem-connectors-panel";

const AuditLogGrid = dynamic(
  () => import("@/components/audit-explorer/audit-log-grid").then((mod) => mod.AuditLogGrid),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[520px] items-center justify-center rounded-md border border-border/60 bg-muted/20">
        <p className="text-sm text-muted-foreground">Loading audit grid…</p>
      </div>
    ),
  }
);

export function AuditExplorerView() {
  const token = useAuthStore((s) => s.token);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [live, setLive] = useState(true);
  const [gridApi, setGridApi] = useState<GridApi<AuditLogEntry> | null>(null);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const { data: logs = [], recentIds, isFetching, dataUpdatedAt } = useAuditLogs(
    search,
    statusFilter,
    live
  );

  const { data: ingestSources = [] } = useQuery({
    queryKey: ["audit-ingest-sources", token],
    queryFn: () => api.getAuditIngestSources(token!),
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : null;

  const handleExport = useCallback(() => {
    gridApi?.exportDataAsCsv({
      fileName: `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`,
    });
  }, [gridApi]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[200px] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search audit logs…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex h-9 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm outline-none ring-ring focus-visible:ring-2"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {["all", "allowed", "blocked", "review"].map((s) => (
            <Button
              key={s}
              variant={statusFilter === s ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(s)}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </Button>
          ))}
        </div>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={handleExport} disabled={!gridApi}>
          <Download className="h-3.5 w-3.5" />
          Export CSV
        </Button>
        <Button
          variant={live ? "default" : "outline"}
          size="sm"
          className="gap-1.5"
          onClick={() => setLive((value) => !value)}
        >
          {live ? <Radio className="h-3.5 w-3.5 animate-pulse" /> : <Pause className="h-3.5 w-3.5" />}
          {live ? "Live" : "Paused"}
        </Button>
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle>Audit Log ({logs.length} entries)</CardTitle>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {ingestSources.length > 0 && (
              <span className="flex flex-wrap items-center gap-1">
                Sources:
                {ingestSources.map((row) => (
                  <Badge key={row.source} variant="outline" className="text-[10px]">
                    {row.source} ({row.count})
                  </Badge>
                ))}
              </span>
            )}
            {live && (
              <Badge variant="success" className="gap-1">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                Real-time
              </Badge>
            )}
            {lastUpdated && <span>{isFetching ? "Refreshing…" : `Updated ${lastUpdated}`}</span>}
          </div>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <AuditLogGrid
            rows={logs}
            recentIds={recentIds}
            quickFilterText={search}
            onGridReady={setGridApi}
          />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
            <span>
              AG Grid: sort, filter, and paginate columns · {formatDateRangeLabel(from, to)}
              {live ? " · auto-refresh every 3s" : " · live updates paused"}
            </span>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setLive(true)} disabled={live}>
              <Play className="h-3.5 w-3.5" />
              Resume live
            </Button>
          </div>
        </CardContent>
      </Card>

      <SiemConnectorsPanel />
    </div>
  );
}
