"use client";

import { useMemo } from "react";
import {
  BarChart3,
  CalendarClock,
  Download,
  Eye,
  FileCheck,
  FileText,
  Loader2,
  Pencil,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { ReportCatalogEntry } from "@/lib/types/domain";
import { buildReportSparkline } from "@/lib/report-preview-utils";
import { cn } from "@/lib/utils";

const statusVariant = {
  ready: "success" as const,
  scheduled: "warning" as const,
  generating: "secondary" as const,
};

const CATEGORY_META: Record<string, { icon: LucideIcon; color: string; bar: string }> = {
  Compliance: { icon: FileCheck, color: "text-blue-400", bar: "bg-blue-400" },
  Security: { icon: ShieldAlert, color: "text-red-400", bar: "bg-red-400" },
  Finance: { icon: TrendingUp, color: "text-emerald-400", bar: "bg-emerald-400" },
  Operations: { icon: BarChart3, color: "text-violet-400", bar: "bg-violet-400" },
  Executive: { icon: FileText, color: "text-amber-400", bar: "bg-amber-400" },
};

function categoryMeta(category: string) {
  return CATEGORY_META[category] ?? { icon: FileText, color: "text-muted-foreground", bar: "bg-primary" };
}

function ReportSparkline({ values, barClass }: { values: number[]; barClass: string }) {
  const max = Math.max(...values, 1);
  return (
    <div className="flex h-8 items-end gap-0.5" aria-hidden>
      {values.map((value, index) => (
        <div
          key={index}
          className={cn("w-1.5 rounded-sm opacity-80", barClass)}
          style={{ height: `${Math.max(12, (value / max) * 100)}%` }}
        />
      ))}
    </div>
  );
}

function IconAction({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          aria-label={label}
          disabled={disabled}
          onClick={onClick}
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="top">{label}</TooltipContent>
    </Tooltip>
  );
}

interface ReportCatalogTableProps {
  catalog: ReportCatalogEntry[];
  canEdit: boolean;
  downloading: string | null;
  onPreview: (report: ReportCatalogEntry) => void;
  onDownload: (report: ReportCatalogEntry) => void;
  onQuery: (report: ReportCatalogEntry) => void;
  onSchedule: (report: ReportCatalogEntry) => void;
}

export function ReportCatalogTable({
  catalog,
  canEdit,
  downloading,
  onPreview,
  onDownload,
  onQuery,
  onSchedule,
}: ReportCatalogTableProps) {
  const recentReports = useMemo(
    () =>
      [...catalog]
        .sort((a, b) => b.last_generated.localeCompare(a.last_generated))
        .slice(0, 5),
    [catalog]
  );

  return (
    <div className="space-y-5">
      {recentReports.length > 0 && (
        <section className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recently generated</p>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
            {recentReports.map((report) => {
              const meta = categoryMeta(report.category);
              const Icon = meta.icon;
              return (
                <div
                  key={`recent-${report.id}`}
                  className="flex items-center justify-between gap-2 rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <Icon className={cn("h-3.5 w-3.5 shrink-0", meta.color)} />
                      <p className="truncate text-sm font-medium">{report.name}</p>
                    </div>
                    <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">{report.last_generated}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-0.5">
                    <IconAction label="Preview data" onClick={() => onPreview(report)}>
                      <Eye className="h-4 w-4" />
                    </IconAction>
                    <IconAction
                      label={`Download ${report.format}`}
                      disabled={downloading === report.id}
                      onClick={() => onDownload(report)}
                    >
                      {downloading === report.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                    </IconAction>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="pb-3 pr-4 font-medium">Report</th>
              <th className="pb-3 pr-4 font-medium">Activity</th>
              <th className="pb-3 pr-4 font-medium">Category</th>
              <th className="pb-3 pr-4 font-medium">Frequency</th>
              <th className="pb-3 pr-4 font-medium">Last run</th>
              <th className="pb-3 pr-4 font-medium">Status</th>
              <th className="pb-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {catalog.map((report) => {
              const meta = categoryMeta(report.category);
              const Icon = meta.icon;
              const rowCount = report.stats?.row_count ?? 0;
              const sparkline = buildReportSparkline(rowCount, report.id);
              return (
                <tr key={report.id} className="border-b border-border/50 last:border-0">
                  <td className="py-3 pr-4">
                    <div className="flex items-start gap-2.5">
                      <div className={cn("mt-0.5 rounded-md bg-muted/40 p-1.5", meta.color)}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{report.name}</p>
                          {report.is_builtin && (
                            <Badge variant="outline" className="text-[10px]">
                              Built-in
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-1">{report.description}</p>
                        {rowCount > 0 && (
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            {rowCount.toLocaleString()} rows in last run
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    <ReportSparkline values={sparkline} barClass={meta.bar} />
                  </td>
                  <td className="py-3 pr-4">
                    <Badge variant="outline" className="font-normal">
                      {report.category}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4">{report.frequency}</td>
                  <td className="py-3 pr-4 font-mono text-xs">{report.last_generated}</td>
                  <td className="py-3 pr-4">
                    <Badge variant={statusVariant[report.status]}>{report.status}</Badge>
                  </td>
                  <td className="py-3">
                    <div className="flex items-center justify-end gap-0.5">
                      <IconAction label="Preview data" onClick={() => onPreview(report)}>
                        <Eye className="h-4 w-4" />
                      </IconAction>
                      <IconAction
                        label={`Download ${report.format}`}
                        disabled={downloading === report.id}
                        onClick={() => onDownload(report)}
                      >
                        {downloading === report.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                      </IconAction>
                      {canEdit && (
                        <>
                          <IconAction label="Edit query" onClick={() => onQuery(report)}>
                            <Pencil className="h-4 w-4" />
                          </IconAction>
                          <IconAction label="Schedule delivery" onClick={() => onSchedule(report)}>
                            <CalendarClock className="h-4 w-4" />
                          </IconAction>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
