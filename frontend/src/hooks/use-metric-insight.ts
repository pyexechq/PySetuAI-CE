"use client";

import { useRef, useState } from "react";
import { ApiError, api, type ApiDashboardMetricInsight } from "@/lib/api";
import type { DashboardMetricKey, MetricInsightClickContext } from "@/lib/dashboard-metric-insights";
import { useAuthStore } from "@/stores/auth-store";

export function useMetricInsight() {
  const token = useAuthStore((s) => s.token);
  const requestSeq = useRef(0);
  const [activeMetric, setActiveMetric] = useState<DashboardMetricKey | null>(null);
  const [activeContext, setActiveContext] = useState<MetricInsightClickContext | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);
  const [insight, setInsight] = useState<ApiDashboardMetricInsight | null>(null);
  const [insightError, setInsightError] = useState<string | null>(null);

  async function openMetricInsight(metricKey: DashboardMetricKey, context: MetricInsightClickContext) {
    if (!token) return;
    const seq = ++requestSeq.current;
    (document.activeElement as HTMLElement | null)?.blur();
    setActiveMetric(metricKey);
    setActiveContext(context);
    setInsightLoading(true);
    setInsight(null);
    setInsightError(null);
    try {
      const result = await api.getDashboardMetricInsight(token, metricKey, {
        card_title: context.cardTitle,
        display_value: context.displayValue,
        period_label: context.periodLabel,
        change: context.change,
      });
      if (seq !== requestSeq.current) return;
      setInsight(result);
    } catch (err) {
      if (seq !== requestSeq.current) return;
      setInsightError(err instanceof ApiError ? err.message : "Unable to load metric insights.");
    } finally {
      if (seq === requestSeq.current) {
        setInsightLoading(false);
      }
    }
  }

  function closeMetricInsight() {
    requestSeq.current += 1;
    setActiveMetric(null);
    setActiveContext(null);
    setInsight(null);
    setInsightError(null);
    setInsightLoading(false);
  }

  return {
    openMetricInsight,
    closeMetricInsight,
    activeMetric,
    activeContext,
    insightLoading,
    insight,
    insightError,
    insightOpen: activeMetric !== null,
  };
}
