"use client";

import { cn, formatNumber, formatCurrency } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { DASHBOARD_METRIC_TOOLTIP, type DashboardMetricKey } from "@/lib/dashboard-metric-insights";
import { type LucideIcon, TrendingUp, TrendingDown, Sparkles } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  change: number;
  icon: LucideIcon;
  iconColor?: string;
  format?: "number" | "currency" | "percent" | "raw";
  periodLabel?: string;
  invertTrend?: boolean;
  insightKey?: DashboardMetricKey;
  onInsightClick?: (metricKey: DashboardMetricKey) => void;
}

export function MetricCard({
  title,
  value,
  change,
  icon: Icon,
  iconColor = "text-primary",
  format = "number",
  periodLabel = "vs prior 30 days",
  invertTrend = false,
  insightKey,
  onInsightClick,
}: MetricCardProps) {
  const isPositive = invertTrend ? change <= 0 : change >= 0;
  const formattedValue =
    format === "currency"
      ? formatCurrency(Number(value))
      : format === "percent"
        ? `${value}%`
        : format === "number"
          ? formatNumber(Number(value))
          : value;

  return (
    <Card className="group relative border-border/60 bg-card/50 transition-colors hover:border-border">
      <CardContent className="p-5">
        {insightKey && onInsightClick && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label={DASHBOARD_METRIC_TOOLTIP}
                onClick={(event) => {
                  event.stopPropagation();
                  onInsightClick(insightKey);
                }}
                className={cn(
                  "absolute right-3 top-3 rounded-md border border-border/60 bg-background/90 p-1.5 text-indigo-400 shadow-sm",
                  "opacity-0 transition-opacity focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  "group-hover:opacity-100"
                )}
              >
                <Sparkles className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="left">{DASHBOARD_METRIC_TOOLTIP}</TooltipContent>
          </Tooltip>
        )}

        <div className="flex items-start justify-between">
          <div className="space-y-2 pr-8">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold tracking-tight">{formattedValue}</p>
            <div className="flex items-center gap-1 text-xs">
              {isPositive ? (
                <TrendingUp className="h-3 w-3 text-emerald-400" />
              ) : (
                <TrendingDown className="h-3 w-3 text-red-400" />
              )}
              <span className={cn(isPositive ? "text-emerald-400" : "text-red-400")}>
                {isPositive ? "+" : ""}
                {change}%
              </span>
              <span className="text-muted-foreground">{periodLabel}</span>
            </div>
          </div>
          <div className={cn("rounded-lg bg-muted/50 p-2.5", iconColor)}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
