"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Activity,
  CalendarClock,
  Download,
  ExternalLink,
  FileCheck,
  FileText,
  Pencil,
  Play,
  Plus,
  Radar,
  ShieldAlert,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/dashboard/metric-card";
import { ReportManagementModals } from "@/components/reports/report-management-modals";
import { CompoundingCostCard } from "@/components/reports/compounding-cost-card";
import { QuickLinkPills, SectionHeading, SectionTabBar } from "@/components/shared/section-chrome";
import { useReports } from "@/hooks/use-reports";
import type { ReportCatalogEntry } from "@/lib/types/domain";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const QUICK_LINKS = [
  { href: "/monitoring", label: "Monitoring", icon: Radar },
  { href: "/monitoring?tab=security", label: "Security", icon: ShieldAlert },
  { href: "/compliance", label: "Compliance", icon: FileCheck },
] as const;

const statusVariant = {
  ready: "success" as const,
  scheduled: "warning" as const,
  generating: "secondary" as const,
};

type DetailTab = "catalog" | "summary" | "scheduler";

function parseKpiChange(change: string): number {
  const n = parseFloat(change.replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function kpiIcon(label: string) {
  if (label.toLowerCase().includes("block") || label.toLowerCase().includes("risk")) return ShieldAlert;
  if (label.toLowerCase().includes("allowed")) return FileCheck;
  return Activity;
}

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
  downloadBlob(filename, blob);
}

export function ReportsView() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const canEdit = user?.role === "tenant_admin" || user?.role === "security_admin";
  const { summary, catalog, templates, invalidateCatalog } = useReports();

  const [detailTab, setDetailTab] = useState<DetailTab>("catalog");
  const [downloading, setDownloading] = useState<string | null>(null);
  const [schedulerMessage, setSchedulerMessage] = useState<string | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "query" | "schedule" | null>(null);
  const [activeReport, setActiveReport] = useState<ReportCatalogEntry | null>(null);

  const tabs: { id: DetailTab; label: string }[] = canEdit
    ? [
        { id: "catalog", label: "Report catalog" },
        { id: "summary", label: "Period summary" },
        { id: "scheduler", label: "Scheduler" },
      ]
    : [
        { id: "catalog", label: "Report catalog" },
        { id: "summary", label: "Period summary" },
      ];

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
          : "No reports are due right now."
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
      downloadCsv(`pysetu-${report.id}-${new Date().toISOString().slice(0, 10)}.csv`, [
        ["Report", report.name],
        ["Format", report.format],
        ["Note", "Run failed — export metadata only"],
      ]);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="space-y-8">
      <QuickLinkPills links={QUICK_LINKS} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Reporting period</p>
          <p className="text-lg font-semibold">{summary.period}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="success">Compliance {summary.compliance_score}%</Badge>
          {canEdit && (
            <Button size="sm" className="gap-1.5" onClick={() => openModal("create")}>
              <Plus className="h-4 w-4" />
              New report
            </Button>
          )}
        </div>
      </div>

      {summary.kpis.length > 0 && (
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {summary.kpis.slice(0, 4).map((kpi) => {
            const Icon = kpiIcon(kpi.label);
            const invertTrend =
              kpi.label.toLowerCase().includes("block") || kpi.label.toLowerCase().includes("risk");
            return (
              <MetricCard
                key={kpi.label}
                variant="hero"
                title={kpi.label}
                value={kpi.value}
                change={parseKpiChange(kpi.change)}
                periodLabel="vs prior period"
                invertTrend={invertTrend}
                icon={Icon}
                iconColor={invertTrend ? "text-red-400" : "text-emerald-400"}
                format="raw"
              />
            );
          })}
        </section>
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionHeading title="Reports & exports" />
          <SectionTabBar tabs={tabs} active={detailTab} onChange={setDetailTab} />
        </div>

        {detailTab === "catalog" && (
          <Card className="border-border/60 bg-card/50">
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-3">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileText className="h-4 w-4" />
                  Report catalog
                </CardTitle>
                <CardDescription className="mt-1">
                  Run or download point-in-time exports. Live analytics stay in Monitoring and Compliance.
                </CardDescription>
              </div>
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
                      <th className="pb-3 pr-4 font-medium">Last run</th>
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
                          <p className="text-xs text-muted-foreground line-clamp-1">{report.description}</p>
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
                                  variant="ghost"
                                  size="sm"
                                  className="gap-1.5"
                                  onClick={() => openModal("query", report)}
                                >
                                  <Pencil className="h-3.5 w-3.5" />
                                  Query
                                </Button>
                                <Button
                                  variant="ghost"
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
        )}

        {detailTab === "summary" && (
          <div className="space-y-4">
            <CompoundingCostCard data={summary.cost_optimization} />
            {summary.top_risks.length > 0 && (
              <Card className="border-border/60 bg-card/50">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <ShieldAlert className="h-4 w-4" />
                    Risk highlights
                  </CardTitle>
                  <CardDescription>Summary for {summary.period}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {summary.top_risks.map((risk, i) => (
                    <div key={risk} className="flex items-start gap-3 rounded-md border border-border/60 p-3 text-sm">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-500/10 text-xs font-bold text-red-400">
                        {i + 1}
                      </span>
                      <span>{risk}</span>
                    </div>
                  ))}
                  <p className="pt-1 text-xs text-muted-foreground">
                    Frameworks: {summary.frameworks_compliant}/{summary.frameworks_total} compliant ·{" "}
                    <Link href="/compliance" className="text-primary hover:underline">
                      Compliance Center
                    </Link>
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {detailTab === "scheduler" && canEdit && (
          <Card className="border-border/60 bg-card/50">
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <CalendarClock className="h-4 w-4" />
                  Report scheduler
                </CardTitle>
                <CardDescription className="mt-1">Celery beat checks every minute for due deliveries.</CardDescription>
              </div>
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
              {schedulerStatus.isLoading && <p className="text-muted-foreground">Loading scheduler status…</p>}
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
            </CardContent>
          </Card>
        )}
      </section>

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
