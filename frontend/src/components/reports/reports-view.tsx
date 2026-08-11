"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  CalendarClock,
  Download,
  ExternalLink,
  FileText,
  Pencil,
  Play,
  Plus,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReportManagementModals } from "@/components/reports/report-management-modals";
import { EMPTY_DASHBOARD_OVERVIEW, mapSecurityTrends, useDashboardOverview } from "@/hooks/use-dashboard-overview";
import { useReports } from "@/hooks/use-reports";
import type { ReportCatalogEntry } from "@/lib/types/domain";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

const statusVariant = {
  ready: "success" as const,
  scheduled: "warning" as const,
  generating: "secondary" as const,
};

function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function downloadCsv(filename: string, rows: string[][]) {
  const csv = rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function ReportsView() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";
  const { summary, catalog, templates, invalidateCatalog } = useReports();
  const { data: overview } = useDashboardOverview();
  const securityTrends = mapSecurityTrends(overview ?? EMPTY_DASHBOARD_OVERVIEW);
  const complianceFrameworks = overview?.compliance_frameworks ?? EMPTY_DASHBOARD_OVERVIEW.compliance_frameworks;

  const [downloading, setDownloading] = useState<string | null>(null);
  const [schedulerMessage, setSchedulerMessage] = useState<string | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "query" | "schedule" | null>(null);
  const [activeReport, setActiveReport] = useState<ReportCatalogEntry | null>(null);

  const schedulerStatus = useQuery({
    queryKey: ["report-scheduler-status", token],
    enabled: Boolean(token && canEdit),
    queryFn: () => api.getReportSchedulerStatus(token!),
    refetchInterval: 30_000,
  });

  const runDueReports = useMutation({
    mutationFn: () => api.runDueScheduledReports(token!),
    onSuccess: (result) => {
      setSchedulerMessage(
        result.enqueued > 0
          ? `Queued ${result.enqueued} scheduled report(s). Check Mailhog for delivery.`
          : "No reports are due right now. Enable a schedule with a past next-run time to test."
      );
      void schedulerStatus.refetch();
      invalidateCatalog();
    },
    onError: (err) => {
      setSchedulerMessage(err instanceof ApiError ? err.message : "Failed to run due reports");
    },
  });

  function openModal(mode: "create" | "query" | "schedule", report?: ReportCatalogEntry) {
    setModalMode(mode);
    setActiveReport(report ?? null);
  }

  function closeModal() {
    setModalMode(null);
    setActiveReport(null);
  }

  async function handleDownload(report: ReportCatalogEntry) {
    if (!token) return;
    setDownloading(report.id);
    invalidateCatalog();
    try {
      await api.runReport(token, report.id);
      invalidateCatalog();
      const { blob, filename } = await api.downloadReport(token, report.id);
      downloadBlob(filename, blob);
      invalidateCatalog();
    } catch {
      downloadCsv(`helixguard-${report.id}-${new Date().toISOString().slice(0, 10)}.csv`, [
        ["Report", report.name],
        ["Format", report.format],
        ["Note", "Run failed — export metadata only"],
      ]);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">Executive reporting period</p>
          <p className="text-xl font-semibold">{summary.period}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="success">Compliance {summary.compliance_score}%</Badge>
          {canEdit && (
            <Button size="sm" className="gap-1.5" onClick={() => openModal("create")}>
              <Plus className="h-4 w-4" />
              New Report
            </Button>
          )}
        </div>
      </div>

      {canEdit && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <CalendarClock className="h-4 w-4" />
              Report Scheduler
            </CardTitle>
            <Button
              size="sm"
              className="gap-1.5"
              disabled={!token || runDueReports.isPending}
              onClick={() => {
                setSchedulerMessage(null);
                runDueReports.mutate();
              }}
            >
              <Play className="h-3.5 w-3.5" />
              Run due reports
            </Button>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {schedulerStatus.isLoading && (
              <p className="text-muted-foreground">Loading scheduler status…</p>
            )}
            {schedulerStatus.isError && (
              <p className="text-red-400">
                {schedulerStatus.error instanceof ApiError
                  ? schedulerStatus.error.message
                  : "Could not load scheduler status"}
              </p>
            )}
            {schedulerStatus.data && (
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-muted-foreground">
                <span>
                  Due now:{" "}
                  <span className="font-medium text-foreground">{schedulerStatus.data.due_reports}</span>
                </span>
                <span>
                  Email:{" "}
                  <span className="font-medium text-foreground">
                    {schedulerStatus.data.smtp_enabled ? schedulerStatus.data.smtp_host : "disabled"}
                  </span>
                </span>
                {schedulerStatus.data.mailhog_ui && (
                  <a
                    href={schedulerStatus.data.mailhog_ui}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline"
                  >
                    Open Mailhog
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            )}
            {schedulerMessage && <p className="text-xs text-muted-foreground">{schedulerMessage}</p>}
            <p className="text-xs text-muted-foreground">
              Celery beat checks every minute. Use this button for a manual run (requires POST + admin login — not a browser GET).
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {summary.kpis.map((kpi) => (
          <Card key={kpi.label} className="border-border/60 bg-card/50">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">{kpi.label}</p>
              <p className="mt-1 text-2xl font-bold">{kpi.value}</p>
              <div className="mt-2 flex items-center gap-1 text-xs">
                {kpi.trend === "up" ? (
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                ) : kpi.trend === "down" ? (
                  <TrendingDown className="h-3.5 w-3.5 text-emerald-400" />
                ) : null}
                <span className="text-muted-foreground">{kpi.change}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/50 lg:col-span-2">
          <CardHeader>
            <CardTitle>Security Activity Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {securityTrends.length === 0 ? (
              <p className="py-16 text-center text-sm text-muted-foreground">No security activity in this period</p>
            ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={securityTrends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    border: "1px solid #334155",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="allowed" fill="#22c55e" name="Allowed" radius={[4, 4, 0, 0]} />
                <Bar dataKey="blocked" fill="#ef4444" name="Blocked" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4" />
              Top Risks
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {summary.top_risks.map((risk, i) => (
              <div key={risk} className="flex items-start gap-3 rounded-md border border-border/60 p-3 text-sm">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-500/10 text-xs font-bold text-red-400">
                  {i + 1}
                </span>
                <span>{risk}</span>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">
              Frameworks: {summary.frameworks_compliant}/{summary.frameworks_total} compliant
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Report Catalog
          </CardTitle>
          <Badge variant="outline">{catalog.length} reports</Badge>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="pb-3 pr-4 font-medium">Report</th>
                  <th className="pb-3 pr-4 font-medium">Category</th>
                  <th className="pb-3 pr-4 font-medium">Frequency</th>
                  <th className="pb-3 pr-4 font-medium">Last Generated</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {catalog.map((report) => (
                  <tr key={report.id} className="border-b border-border/50 last:border-0">
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{report.name}</p>
                        {report.is_builtin && (
                          <Badge variant="outline" className="text-[10px]">
                            Built-in
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{report.description}</p>
                      {report.query && (
                        <p className="mt-1 font-mono text-[10px] text-muted-foreground/80">
                          {report.query.source} · limit {report.query.limit}
                        </p>
                      )}
                      {report.schedule?.enabled && report.schedule.recipients && report.schedule.recipients.length > 0 && (
                        <p className="mt-1 text-[10px] text-muted-foreground">
                          Delivers to: {report.schedule.recipients.join(", ")}
                        </p>
                      )}
                    </td>
                    <td className="py-3 pr-4">{report.category}</td>
                    <td className="py-3 pr-4">{report.frequency}</td>
                    <td className="py-3 pr-4 font-mono text-xs">{report.last_generated}</td>
                    <td className="py-3 pr-4">
                      <Badge variant={statusVariant[report.status]}>{report.status}</Badge>
                    </td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-1.5">
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1.5"
                          disabled={downloading === report.id}
                          onClick={() => handleDownload(report)}
                        >
                          <Download className="h-3.5 w-3.5" />
                          {report.format}
                        </Button>
                        {canEdit && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              className="gap-1.5"
                              onClick={() => openModal("query", report)}
                            >
                              <Pencil className="h-3.5 w-3.5" />
                              Query
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="gap-1.5"
                              onClick={() => openModal("schedule", report)}
                            >
                              <CalendarClock className="h-3.5 w-3.5" />
                              Schedule
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!canEdit && (
            <p className="mt-3 text-xs text-muted-foreground">
              Tenant Admin or Security Admin role required to create, schedule, or edit report queries.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {complianceFrameworks.map((fw) => (
          <Card key={fw.name} className="border-border/60 bg-card/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <p className="font-medium">{fw.name}</p>
                <Badge variant={fw.status === "compliant" ? "success" : "warning"}>{fw.score}%</Badge>
              </div>
              <p className={cn("mt-1 text-xs capitalize text-muted-foreground", fw.status === "at-risk" && "text-red-400")}>
                {fw.passed}/{fw.controls} controls passed
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <ReportManagementModals
        key={`${modalMode ?? "closed"}-${activeReport?.id ?? "new"}`}
        mode={modalMode}
        report={activeReport}
        templates={templates}
        token={token}
        canEdit={canEdit}
        onClose={closeModal}
        onSaved={invalidateCatalog}
      />
    </div>
  );
}
