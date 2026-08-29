"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Activity,
  CalendarClock,
  ExternalLink,
  FileCheck,
  FileText,
  Play,
  Plus,
  Radar,
  ShieldAlert,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/dashboard/metric-card";
import { MetricInsightModal } from "@/components/dashboard/metric-insight-modal";
import { ReportManagementModals } from "@/components/reports/report-management-modals";
import { ReportCatalogTable } from "@/components/reports/report-catalog-table";
import { ReportPreviewModal } from "@/components/reports/report-preview-modal";
import { CompoundingCostCard } from "@/components/reports/compounding-cost-card";
import { QuickLinkPills, SectionHeading, SectionTabBar } from "@/components/shared/section-chrome";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useReports } from "@/hooks/use-reports";
import { useMetricInsight } from "@/hooks/use-metric-insight";
import type { ReportCatalogEntry } from "@/lib/types/domain";
import { resolveMetricInsightKey } from "@/lib/dashboard-metric-insights";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const QUICK_LINKS = [
  { href: "/monitoring", label: "Monitoring", icon: Radar },
  { href: "/monitoring?tab=security", label: "Security", icon: ShieldAlert },
  { href: "/compliance", label: "Compliance", icon: FileCheck },
] as const;

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
  const [previewReport, setPreviewReport] = useState<ReportCatalogEntry | null>(null);
  const {
    openMetricInsight,
    closeMetricInsight,
    insightOpen,
    activeContext,
    insightLoading,
    insight,
    insightError,
  } = useMetricInsight();

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
    <TooltipProvider delayDuration={200}>
      <div className="space-y-6">
        <QuickLinkPills links={QUICK_LINKS} />

        {/* ─── Hero Glassmorphic Telemetry Ribbon ───────────────────────────────── */}
        <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-br from-card via-card/90 to-muted/30 p-4 sm:p-6 shadow-sm">
          <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between w-full min-w-0">
            <div className="space-y-2.5 w-full min-w-0 max-w-xl">
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold gap-1.5 px-2.5 py-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  Scheduled Exports Active
                </Badge>
                <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 text-xs font-medium gap-1">
                  <FileText className="h-3.5 w-3.5 text-primary" />
                  CSV / JSON / PDF Generator
                </Badge>
                <Badge variant="outline" className="bg-muted text-muted-foreground border-border/60 text-xs font-mono">
                  {summary.period}
                </Badge>
              </div>

              <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-foreground break-words">
                Executive Reports & Compliance Exports
              </h1>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                Generate auditable point-in-time compliance reports, compounding token cost breakdowns, and security incident logs for external regulators.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <Badge variant="success" className="text-xs py-1 px-3">Compliance {summary.compliance_score}%</Badge>
              {canEdit && (
                <Button size="sm" className="gap-1.5 text-xs h-8" onClick={() => openModal("create")}>
                  <Plus className="h-3.5 w-3.5" />
                  Generate Custom Report
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* ─── Navigation Tabs ──────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-card/60 border border-border/50 shadow-xs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setDetailTab(tab.id)}
                className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
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

        <div className="space-y-4">
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
              <ReportCatalogTable
                catalog={catalog}
                canEdit={canEdit}
                downloading={downloading}
                onPreview={setPreviewReport}
                onDownload={handleDownload}
                onQuery={(report) => openModal("query", report)}
                onSchedule={(report) => openModal("schedule", report)}
              />
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
      </div>

      <ReportPreviewModal
        report={previewReport}
        token={token}
        onClose={() => setPreviewReport(null)}
      />

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

      <MetricInsightModal
        open={insightOpen}
        loading={insightLoading}
        insight={insight}
        error={insightError}
        pendingTitle={activeContext?.cardTitle}
        onClose={closeMetricInsight}
      />
    </div>
    </TooltipProvider>
  );
}
