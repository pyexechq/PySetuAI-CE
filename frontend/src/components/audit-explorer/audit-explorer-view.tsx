"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type { GridApi } from "ag-grid-community";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { SiemConnectorsPanel } from "@/components/audit-explorer/siem-connectors-panel";
import { TranslationTracePanel } from "@/components/audit-explorer/translation-trace-panel";
import { RequestLogPanel } from "@/components/audit-explorer/request-log-panel";
import { RequestLogSettingsCard } from "@/components/audit-explorer/request-log-settings-card";
import { TraceReplayPanel } from "@/components/audit-explorer/trace-replay-panel";
import { QuickLinkPills, SectionTabBar } from "@/components/shared/section-chrome";
import { useAuditLogs, useAuditSummary } from "@/hooks/use-audit-logs";
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
  ShieldCheck,
  Lock,
  Sparkles,
} from "lucide-react";

const AuditLogGrid = dynamic(
  () => import("@/components/audit-explorer/audit-log-grid").then((mod) => mod.AuditLogGrid),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[480px] items-center justify-center rounded-2xl border border-border/60 bg-muted/20">
        <p className="text-xs text-muted-foreground font-mono">Loading telemetry stream…</p>
      </div>
    ),
  }
);

const QUICK_LINKS = [
  { href: "/monitoring", label: "Monitoring & SLA", icon: Radar },
  { href: "/ai-gateway", label: "AI Gateway", icon: LayoutDashboard },
  { href: "/compliance", label: "Compliance Posture", icon: FileCheck },
  { href: "/ai-gateway?tab=rag", label: "Governed RAG", icon: ShieldAlert },
] as const;

type DetailTab = "inspect" | "integrations";

const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: "inspect", label: "Event Payload & Traces" },
  { id: "integrations", label: "SIEM & Export Connectors" },
];

export function AuditExplorerView() {
  const token = useAuthStore((s) => s.token);
  const searchParams = useSearchParams();
  const timezone = usePreferencesStore((s) => s.timezone);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [live, setLive] = useState(true);
  const [gridApi, setGridApi] = useState<GridApi<AuditLogEntry> | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const auditIdParam = searchParams.get("audit_id")?.trim() || undefined;
  const requestedTab = searchParams.get("tab");
  const [detailTab, setDetailTab] = useState<DetailTab>(
    requestedTab === "integrations" ? "integrations" : "inspect"
  );
  const { data: logs = [], recentIds, isFetching, isLoading, isError, dataUpdatedAt, hasNextPage, fetchNextPage } = useAuditLogs(
    actionFilter === "rag" ? "RAG" : search,
    statusFilter,
    live,
    auditIdParam,
    sourceFilter
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

  const { data: summaryData } = useAuditSummary(
    actionFilter === "rag" ? "RAG" : search,
    statusFilter,
    auditIdParam,
    sourceFilter
  );

  const statusCounts = useMemo(() => {
    if (summaryData) {
      return summaryData;
    }
    const counts = { total: 0, allowed: 0, blocked: 0, review: 0 };
    for (const log of logs) {
      counts.total += 1;
      if (log.status === "allowed") counts.allowed += 1;
      else if (log.status === "blocked") counts.blocked += 1;
      else if (log.status === "review") counts.review += 1;
    }
    return counts;
  }, [logs, summaryData]);

  useEffect(() => {
    const next = searchParams.get("tab");
    if (next === "integrations" || next === "inspect") setDetailTab(next);
  }, [searchParams]);

  useEffect(() => {
    if (selectedLog) setDetailTab("inspect");
  }, [selectedLog]);

  const handleExport = useCallback(() => {
    gridApi?.exportDataAsCsv({
      fileName: `pysetu-audit-trail-${new Date().toISOString().slice(0, 10)}.csv`,
    });
  }, [gridApi]);

  return (
    <div className="space-y-6">
      <QuickLinkPills links={QUICK_LINKS} />

      {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-6 shadow-sm">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2.5 max-w-xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Live Ingestion Stream
              </Badge>
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                SHA-256 Tamper-Proof Trail
              </Badge>
              <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                SIEM Ready
              </Badge>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              Audit Explorer & Telemetry Trace Mesh
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Cryptographically verified audit trail capturing full request-response lifecycles, Presidio PII redaction diffs, OPA decision logs, and upstream latencies.
            </p>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-3 shrink-0">
            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Total Events</span>
                <Activity className="h-3.5 w-3.5 text-blue-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-foreground">{statusCounts.total || logs.length}</p>
              <p className="text-[10px] text-muted-foreground">Recorded in range</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Allowed Traffic</span>
                <FileCheck className="h-3.5 w-3.5 text-emerald-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-emerald-600 dark:text-emerald-400">{statusCounts.allowed}</p>
              <p className="text-[10px] text-muted-foreground">Policy cleared</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Threats Blocked</span>
                <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-rose-600 dark:text-rose-400">{statusCounts.blocked}</p>
              <p className="text-[10px] text-muted-foreground">Violations intercepted</p>
            </div>

            <div className="rounded-xl border border-border/80 bg-card/80 p-3.5 shadow-xs backdrop-blur-sm min-w-[130px]">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Under Review</span>
                <Search className="h-3.5 w-3.5 text-amber-500" />
              </div>
              <p className="mt-1.5 text-xl font-bold text-amber-600 dark:text-amber-400">{statusCounts.review}</p>
              <p className="text-[10px] text-muted-foreground">Escalated to human</p>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Filter Toolbar & Action Bar ──────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 bg-card/60 p-2.5 rounded-2xl border border-border/80 shadow-xs">
          {/* Search Box */}
          <div className="relative min-w-[220px] flex-1">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search traces by prompt, model, tenant, or trace ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex h-8 w-full rounded-xl border border-border/60 bg-background/80 pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-primary"
            />
          </div>

          {/* Status Filter Segment */}
          <div className="flex items-center gap-1 rounded-xl border border-border/60 bg-muted/30 p-1">
            {["all", "allowed", "blocked", "review"].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStatusFilter(s)}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-all ${
                  statusFilter === s
                    ? "bg-card text-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {s === "all" ? "All Status" : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>

          {/* Source Filter */}
          <select
            id="audit-source-filter"
            value={sourceFilter}
            onChange={(event) => setSourceFilter(event.target.value)}
            className="h-8 rounded-xl border border-border/60 bg-background/80 px-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-primary"
          >
            <option value="all">All Sources</option>
            {ingestSources.map((item) => (
              <option key={item.source} value={item.source}>
                {item.source} ({item.count})
              </option>
            ))}
          </select>

          {/* Action Filter */}
          <div className="flex items-center gap-1 rounded-xl border border-border/60 bg-muted/30 p-1">
            {[
              { id: "all", label: "All Actions" },
              { id: "rag", label: "Governed RAG" },
            ].map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setActionFilter(item.id);
                  if (item.id === "all") setSearch("");
                }}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-all ${
                  actionFilter === item.id
                    ? "bg-card text-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs" onClick={handleExport} disabled={!gridApi}>
              <Download className="h-3.5 w-3.5" />
              Export CSV
            </Button>
            <Button
              variant={live ? "default" : "outline"}
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => setLive((value) => !value)}
            >
              {live ? <Radio className="h-3.5 w-3.5 animate-pulse text-emerald-400" /> : <Pause className="h-3.5 w-3.5" />}
              {live ? "Live Stream" : "Paused"}
            </Button>
          </div>
        </div>

        {/* ─── Grid Container ───────────────────────────────────────────────── */}
        <div className="rounded-2xl border border-border/80 bg-card/60 p-4 shadow-xs space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-2.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-foreground">Live Telemetry Events</span>
              {live && (
                <Badge variant="success" className="gap-1 text-[10px] py-0 px-1.5 font-mono">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                  Streaming
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
              {lastUpdated && <span>{isFetching ? "Syncing…" : `Last sync: ${lastUpdated}`}</span>}
            </div>
          </div>

          {isError ? (
            <div className="flex h-[280px] items-center justify-center rounded-xl border border-border/60 bg-muted/10 px-6 text-center">
              <p className="text-xs text-muted-foreground">Could not load audit logs. Check your connection.</p>
            </div>
          ) : isLoading && logs.length === 0 ? (
            <div className="flex h-[280px] items-center justify-center rounded-xl border border-border/60 bg-muted/20">
              <p className="text-xs text-muted-foreground font-mono">Streaming telemetry packets…</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="flex h-[280px] items-center justify-center rounded-xl border border-border/60 bg-muted/10 px-6 text-center">
              <p className="text-xs text-muted-foreground">No audit events found. Adjust your filters or generate gateway traffic.</p>
            </div>
          ) : (
            <AuditLogGrid
              rows={logs}
              recentIds={recentIds}
              quickFilterText={search}
              onGridReady={setGridApi}
              onRowSelect={setSelectedLog}
              onLoadMore={() => hasNextPage && fetchNextPage()}
            />
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 text-xs text-muted-foreground border-t border-border/50">
            <span>
              {formatDateRangeLabel(from, to)} {live ? " · Real-time auto-refresh" : " · Stream paused"}
            </span>
            {!live && (
              <Button variant="ghost" size="sm" className="h-6 gap-1 text-xs" onClick={() => setLive(true)}>
                <Play className="h-3 w-3 text-primary" /> Resume Live
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* ─── Detail Panels ────────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-bold text-foreground">
              {selectedLog ? `Inspect Event: ${selectedLog.action}` : "Telemetry Payload Inspector"}
            </h2>
            {selectedRouting?.rule && (
              <Badge variant="outline" className="gap-1 border-primary/30 bg-primary/10 text-primary text-xs font-mono">
                <Route className="h-3 w-3" />
                {selectedRouting.label}: {selectedRouting.rule}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
            {DETAIL_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setDetailTab(tab.id)}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                  detailTab === tab.id
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
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
      </div>
    </div>
  );
}
