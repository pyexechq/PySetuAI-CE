"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ExecutiveSummary, ReportCatalogEntry } from "@/lib/mock-data";
import { resolveReportQueryTemplates } from "@/lib/report-query-templates";
import { useAuthStore } from "@/stores/auth-store";
import { useDateRangeStore } from "@/stores/date-range-store";

function mapCatalogEntry(r: Awaited<ReturnType<typeof api.getReportCatalog>>["reports"][0]): ReportCatalogEntry {
  return {
    ...r,
    status: r.status as ReportCatalogEntry["status"],
  };
}

const EMPTY_SUMMARY: ExecutiveSummary = {
  period: "—",
  kpis: [],
  compliance_score: 0,
  frameworks_compliant: 0,
  frameworks_total: 0,
  top_risks: [],
};

export function useReports() {
  const token = useAuthStore((s) => s.token);
  const from = useDateRangeStore((s) => s.from);
  const to = useDateRangeStore((s) => s.to);
  const queryClient = useQueryClient();

  const summaryQuery = useQuery({
    queryKey: ["executive-summary", token, from, to],
    queryFn: async () => {
      const data = await api.getExecutiveSummary(token!, { from_date: from, to_date: to });
      return {
        ...data,
        kpis: data.kpis.map((k) => ({
          ...k,
          trend: k.trend as ExecutiveSummary["kpis"][0]["trend"],
        })),
      } satisfies ExecutiveSummary;
    },
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  const catalogQuery = useQuery({
    queryKey: ["report-catalog", token],
    queryFn: () => api.getReportCatalog(token!).then((data) => data.reports.map(mapCatalogEntry)),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const templatesQuery = useQuery({
    queryKey: ["report-query-templates", token],
    queryFn: () => api.getReportQueryTemplates(token!).then((data) => data.templates),
    enabled: Boolean(token),
    staleTime: 300_000,
  });

  function invalidateCatalog() {
    queryClient.invalidateQueries({ queryKey: ["report-catalog"] });
  }

  return {
    summary: summaryQuery.data ?? EMPTY_SUMMARY,
    catalog: catalogQuery.data ?? [],
    templates: resolveReportQueryTemplates(templatesQuery.data ?? []),
    isLoadingTemplates: templatesQuery.isLoading,
    invalidateCatalog,
    isLoadingCatalog: catalogQuery.isLoading,
    isLoadingSummary: summaryQuery.isLoading,
  };
}
