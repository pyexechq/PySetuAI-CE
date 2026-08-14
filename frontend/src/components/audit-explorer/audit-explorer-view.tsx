"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type { GridApi } from "ag-grid-community";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MetricStrip } from "@/components/dashboard/metric-card";
import { SiemConnectorsPanel } from "@/components/audit-explorer/siem-connectors-panel";
import { TranslationTracePanel } from "@/components/audit-explorer/translation-trace-panel";
import { RequestLogPanel } from "@/components/audit-explorer/request-log-panel";
import { RequestLogSettingsCard } from "@/components/audit-explorer/request-log-settings-card";
import { TraceReplayPanel } from "@/components/audit-explorer/trace-replay-panel";
import { QuickLinkPills, SectionHeading, SectionTabBar } from "@/components/shared/section-chrome";
import { useAuditLogs } from "@/hooks/use-audit-logs";
import type { AuditLogEntry } from "@/lib/types/domain";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { formatDateRangeLabel } from "@/lib/date-range";
import { useDateRangeStore } from "@/stores/date-range-store";
import { usePreferencesStore } from "@/stores/preferences-store";
import { formatTime } from "@/lib/date-utils";
import { resolveAuditRoutingRule } from "@/lib/audit-routing";
import {
  Activity,
  Download,
  FileCheck,
  LayoutDashboard,
  Route,
  Pause,
  Play,
  Radar,
  Radio,
  Search,
  ShieldAlert,
} from "lucide-react";

const AuditLogGrid = dynamic(
  () => import("@/components/audit-explorer/audit-log-grid").then((mod) => mod.AuditLogGrid),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[480px] items-center justify-center rounded-md border border-border/60 bg-muted/20">
        <p className="text-sm text-muted-foreground">Loading audit grid…</p>
      </div>
    ),
  }
);

const QUICK_LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/monitoring", label: "Monitoring", icon: Radar },
  { href: "/compliance", label: "Compliance", icon: FileCheck },
  { href: "/ai-gateway?tab=rag", label: "Governed RAG", icon: ShieldAlert },
] as const;

type DetailTab = "inspect" | "integrations";

const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: "inspect", label: "Event inspection" },
  { id: "integrations", label: "Export & SIEM" },
];

export function AuditExplorerView() {
  const token = useAuthStore((s) => s.token);
  const searchParams = useSearchParams();
  const timezone = usePreferencesStore((s) => s.timezone);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [live, setLive] = useState(true);
  const [detailTab, setDetailTab] = useState<DetailTab>("inspect");
  const [gridApi, setGridApi] = useState<GridApi<AuditLogEntry> | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const auditIdParam = searchParams.get("audit_id")?.trim() || undefined;
  const { data: logs = [], recentIds, isFetching, isLoading, isError, dataUpdatedAt } = useAuditLogs(
    actionFilter === "rag" ? "RAG" : search,
    statusFilter,
    live,
    auditIdParam
  );

  const { data: ingestSources = [] } = useQuery({
    queryKey: ["audit-ingest-sources", token],
    queryFn: () => api.getAuditIngestSources(token!),
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  const lastUpdated = dataUpdatedAt ? formatTime(new Date(dataUpdatedAt), timezone) : null;
  const selectedRouting = useMemo(
    () => (selectedLog ? resolveAuditRoutingRule(selectedLog) : null),
    [selectedLog]
  );

  const statusCounts = useMemo(() => {
    const counts = { allowed: 0, blocked: 0, review: 0 };
    for (const log of logs) {
      if (log.status === "allowed") counts.allowed += 1;
      else if (log.status === "blocked") counts.blocked += 1;
      else if (log.status === "review") counts.review += 1;
    }
    return counts;
  }, [logs]);

  useEffect(() => {
    const auditId = searchParams.get("audit_id")?.trim();
    if (auditId) return;
    const q = searchParams.get("q")?.trim();
    if (q) setSearch(q);
  }, [searchParams]);

  useEffect(() => {
    if (selectedLog) setDetailTab("inspect");
  }, [selectedLog]);

  const handleExport = useCallback(() => {
    gridApi?.exportDataAsCsv({
      fileName: `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`,
    });
  }, [gridApi]);

  return (
    <div className="space-y-8">
      <QuickLinkPills links={QUICK_LINKS} />

      <section className="space-y-3">
        <SectionHeading title="Event summary" />
        <MetricStrip
          items={[
            {
              title: "Total events",
              value: logs.length,
              change: 0,
              icon: Activity,
              iconColor: "text-blue-400",
              showTrend: false,
            },
            {
              title: "Allowed",
              value: statusCounts.allowed,
              change: 0,
              icon: FileCheck,
              iconColor: "text-emerald-400",
              showTrend: false,
            },
            {
              title: "Blocked",
              value: statusCounts.blocked,
              change: 0,
              icon: ShieldAlert,
              iconColor: "text-red-400",
              showTrend: false,
            },
            {
              title: "Under review",
              value: statusCounts.review,
              change: 0,
              icon: Search,
              iconColor: "text-amber-400",
              showTrend: false,
            },
          ]}
        />
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
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
          <div className="flex flex-wrap items-center gap-1 rounded-lg border border-border/60 bg-muted/30 p-1">
            {["all", "allowed", "blocked", "review"].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStatusFilter(s)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  statusFilter === s
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-1 rounded-lg border border-border/60 bg-muted/30 p-1">
            {[
              { id: "all", label: "All actions" },
              { id: "rag", label: "RAG governance" },
            ].map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setActionFilter(item.id);
                  if (item.id === "all") setSearch("");
                }}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  actionFilter === item.id
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={handleExport} disabled={!gridApi}>
            <Download className="h-3.5 w-3.5" />
            Export
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

        <div className="rounded-lg border border-border/60 bg-card/50 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium">Audit log</p>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
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
          </div>

          {isError ? (
            <div className="flex h-[280px] items-center justify-center rounded-md border border-border/60 bg-muted/10 px-6 text-center">
              <p className="text-sm text-muted-foreground">
                Could not load audit logs. Check your connection and try again.
              </p>
            </div>
          ) : isLoading && logs.length === 0 ? (
            <div className="flex h-[280px] items-center justify-center rounded-md border border-border/60 bg-muted/20">
              <p className="text-sm text-muted-foreground">Loading audit logs…</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="flex h-[280px] items-center justify-center rounded-md border border-border/60 bg-muted/10 px-6 text-center">
              <p className="text-sm text-muted-foreground">
                No audit events in this range. Adjust filters or wait for gateway traffic.
              </p>
            </div>
          ) : (
            <AuditLogGrid
              rows={logs}
              recentIds={recentIds}
              quickFilterText={search}
              onGridReady={setGridApi}
              onRowSelect={setSelectedLog}
            />
          )}

          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>
              {formatDateRangeLabel(from, to)}
              {live ? " · auto-refresh every 3s" : " · live updates paused"}
            </span>
            <Button variant="ghost" size="sm" className="h-7 gap-1.5 text-xs" onClick={() => setLive(true)} disabled={live}>
              <Play className="h-3 w-3" />
              Resume live
            </Button>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold">
              {selectedLog ? `Selected: ${selectedLog.action}` : "Detail panels"}
            </h2>
            {selectedRouting?.rule && (
              <Badge variant="outline" className="gap-1 border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
                <Route className="h-3 w-3" />
                {selectedRouting.label}: {selectedRouting.rule}
              </Badge>
            )}
            {selectedRouting?.rule && (
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" asChild>
                <Link href="/llm-router">Open LLM Router</Link>
              </Button>
            )}
          </div>
          <SectionTabBar tabs={DETAIL_TABS} active={detailTab} onChange={setDetailTab} />
        </div>

        {detailTab === "inspect" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <TranslationTracePanel entry={selectedLog} />
            <TraceReplayPanel entry={selectedLog} />
            <div className="lg:col-span-2">
              <RequestLogPanel entry={selectedLog} />
            </div>
          </div>
        )}

        {detailTab === "integrations" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <RequestLogSettingsCard />
            <SiemConnectorsPanel />
          </div>
        )}
      </section>
    </div>
  );
}
