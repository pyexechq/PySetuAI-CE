"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, Loader2 } from "lucide-react";
import { AppModal } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { api, ApiError, type ApiReportPreviewResponse } from "@/lib/api";
import type { ReportCatalogEntry } from "@/lib/types/domain";
import { extractReportChartData, extractReportKpis } from "@/lib/report-preview-utils";

const PIE_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

interface ReportPreviewModalProps {
  report: ReportCatalogEntry | null;
  token: string | null;
  onClose: () => void;
}

export function ReportPreviewModal({ report, token, onClose }: ReportPreviewModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ApiReportPreviewResponse | null>(null);
  const [source, setSource] = useState<"cached" | "live">("live");

  useEffect(() => {
    if (!report || !token) {
      setPreview(null);
      setError(null);
      return;
    }

    let cancelled = false;

    async function load() {
      if (!report) return;
      setLoading(true);
      setError(null);
      setPreview(null);
      try {
        try {
          const cached = await api.getReportRunResult(token!, report.id);
          if (!cancelled) {
            setPreview({
              columns: cached.columns,
              rows: cached.rows.slice(0, 50),
              row_count: cached.row_count,
            });
            setSource("cached");
            return;
          }
        } catch (err) {
          if (err instanceof ApiError && err.status !== 404) {
            throw err;
          }
        }

        const live = await api.previewReport(token!, report.id);
        if (!cancelled) {
          setPreview(live);
          setSource("live");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Unable to load report preview");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [report, token]);

  const chart = preview ? extractReportChartData(preview) : null;
  const kpis = preview ? extractReportKpis(preview) : [];

  if (!report) return null;

  return (
    <AppModal
      onClose={onClose}
      title={report.name}
      description={report.description}
      size="2xl"
    >
      {loading && (
        <div className="flex items-center gap-2 py-12 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading report data…
        </div>
      )}

      {!loading && error && <p className="text-sm text-destructive">{error}</p>}

      {!loading && preview && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{report?.category}</Badge>
            <Badge variant="outline">{report?.format}</Badge>
            <Badge variant={source === "cached" ? "success" : "secondary"}>
              {source === "cached" ? "Last generated run" : "Live preview (first 50 rows)"}
            </Badge>
          </div>

          {kpis.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {kpis.map((kpi) => (
                <div key={kpi.label} className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2">
                  <p className="text-xs text-muted-foreground">{kpi.label}</p>
                  <p className="text-lg font-semibold tabular-nums">{kpi.value}</p>
                </div>
              ))}
            </div>
          )}

          {chart?.type === "bar" && (
            <div className="rounded-lg border border-border/60 bg-card/40 p-3">
              <p className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <BarChart3 className="h-3.5 w-3.5" />
                Distribution
              </p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chart.barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="label" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                  <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {chart?.type === "pie" && (
            <div className="rounded-lg border border-border/60 bg-card/40 p-3">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Breakdown</p>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={chart.pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                    {chart.pieData.map((entry, index) => (
                      <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="overflow-x-auto rounded-lg border border-border/60">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/20 text-left text-muted-foreground">
                  {preview.columns.map((column) => (
                    <th key={column} className="px-3 py-2 font-medium">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.length === 0 ? (
                  <tr>
                    <td colSpan={preview.columns.length || 1} className="px-3 py-8 text-center text-muted-foreground">
                      No rows match this report query.
                    </td>
                  </tr>
                ) : (
                  preview.rows.map((row, rowIndex) => (
                    <tr key={rowIndex} className="border-b border-border/40 last:border-0">
                      {preview.columns.map((_, colIndex) => (
                        <td key={colIndex} className="max-w-[14rem] truncate px-3 py-2 font-mono text-xs">
                          {String(row[colIndex] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {preview.row_count > preview.rows.length && (
            <p className="text-xs text-muted-foreground">
              Showing {preview.rows.length} of {preview.row_count.toLocaleString()} rows. Download the full export for
              complete data.
            </p>
          )}
        </div>
      )}
    </AppModal>
  );
}
