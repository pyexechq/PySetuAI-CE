"use client";

import { cn, formatNumber, formatCurrency } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { DASHBOARD_METRIC_TOOLTIP, type DashboardMetricKey, type MetricInsightClickHandler } from "@/lib/dashboard-metric-insights";
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
  onInsightClick?: MetricInsightClickHandler;
  variant?: "default" | "hero" | "compact";
  showTrend?: boolean;
}

function formatMetricValue(value: string | number, format: MetricCardProps["format"]) {
  if (format === "raw") return String(value ?? "—");
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return "—";
  if (format === "currency") return formatCurrency(numeric);
  if (format === "percent") return `${numeric}%`;
  if (format === "number") return formatNumber(numeric);
  return String(value);
}

function TrendBadge({
  change,
  invertTrend,
  periodLabel,
  compact,
}: {
  change: number;
  invertTrend?: boolean;
  periodLabel: string;
  compact?: boolean;
}) {
  const isPositive = invertTrend ? change <= 0 : change >= 0;
  const TrendIcon = isPositive ? TrendingUp : TrendingDown;
  const safeChange = Number.isFinite(change) ? change : 0;

  if (compact) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-medium tabular-nums",
          isPositive ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
        )}
      >
        <TrendIcon className="h-2.5 w-2.5" />
        {isPositive ? "+" : ""}
        {safeChange}%
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1 text-xs">
      <TrendIcon className={cn("h-3 w-3", isPositive ? "text-emerald-400" : "text-red-400")} />
      <span className={cn(isPositive ? "text-emerald-400" : "text-red-400")}>
        {isPositive ? "+" : ""}
        {safeChange}%
      </span>
      <span className="text-muted-foreground">{periodLabel}</span>
    </div>
  );
}

function InsightButton({
  insightKey,
  cardTitle,
  displayValue,
  periodLabel,
  change,
  onInsightClick,
}: {
  insightKey: DashboardMetricKey;
  cardTitle: string;
  displayValue: string;
  periodLabel?: string;
  change?: number;
  onInsightClick: MetricInsightClickHandler;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={DASHBOARD_METRIC_TOOLTIP}
          onClick={(event) => {
            event.stopPropagation();
            onInsightClick(insightKey, {
              cardTitle,
              displayValue,
              periodLabel,
              change,
            });
          }}
          className={cn(
            "rounded-md border border-border/60 bg-background/90 p-1.5 text-indigo-400 shadow-sm",
            "opacity-0 transition-opacity focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            "group-hover:opacity-100"
          )}
        >
          <Sparkles className="h-3.5 w-3.5" />
        </button>
      </TooltipTrigger>
      <TooltipContent side="left">{DASHBOARD_METRIC_TOOLTIP}</TooltipContent>
    </Tooltip>
  );
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
  variant = "default",
  showTrend = true,
}: MetricCardProps) {
  const formattedValue = formatMetricValue(value, format);
  const showInsight = Boolean(insightKey && onInsightClick);
  const insightButtonProps = {
    insightKey: insightKey!,
    cardTitle: title,
    displayValue: formattedValue,
    periodLabel,
    change,
    onInsightClick: onInsightClick!,
  };

  if (variant === "compact") {
    return (
      <div className="group relative flex min-w-0 flex-col gap-1 px-4 py-3 sm:px-5">
        {showInsight && (
          <div className="absolute right-2 top-2">
            <InsightButton {...insightButtonProps} />
          </div>
        )}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Icon className={cn("h-3.5 w-3.5 shrink-0", iconColor)} />
          <span className="truncate">{title}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <p className="text-lg font-semibold tracking-tight tabular-nums">{formattedValue}</p>
          {showTrend && (
            <TrendBadge change={change} invertTrend={invertTrend} periodLabel={periodLabel} compact />
          )}
        </div>
      </div>
    );
  }

  if (variant === "hero") {
    return (
      <Card className="group relative border-border/60 bg-card/50 transition-colors hover:border-border">
        <CardContent className="p-5">
          {showInsight && (
            <div className="absolute right-3 top-3">
              <InsightButton {...insightButtonProps} />
            </div>
          )}
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 space-y-1 pr-6">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
              <p className="text-3xl font-bold tracking-tight tabular-nums">{formattedValue}</p>
              {showTrend && (
                <TrendBadge change={change} invertTrend={invertTrend} periodLabel={periodLabel} />
              )}
            </div>
            <div className={cn("shrink-0 rounded-xl bg-muted/40 p-3", iconColor)}>
              <Icon className="h-5 w-5" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="group relative border-border/60 bg-card/50 transition-colors hover:border-border">
      <CardContent className="p-5">
        {showInsight && (
          <div className="absolute right-3 top-3">
            <InsightButton {...insightButtonProps} />
          </div>
        )}
        <div className="flex items-start justify-between">
          <div className="space-y-2 pr-8">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold tracking-tight">{formattedValue}</p>
            {showTrend && (
              <TrendBadge change={change} invertTrend={invertTrend} periodLabel={periodLabel} />
            )}
          </div>
          <div className={cn("rounded-lg bg-muted/50 p-2.5", iconColor)}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export interface MetricStripItem extends Omit<MetricCardProps, "variant"> {}

export function MetricStrip({
  items,
  onInsightClick,
}: {
  items: MetricStripItem[];
  onInsightClick?: MetricInsightClickHandler;
}) {
  const colClass = items.length === 3 ? "lg:grid-cols-3" : "lg:grid-cols-4";
  return (
    <Card className="border-border/60 bg-card/50 overflow-hidden">
      <div className={cn("grid divide-y sm:grid-cols-2 sm:divide-x sm:divide-y-0", colClass)}>
        {items.map((item) => (
          <MetricCard key={item.title} {...item} variant="compact" onInsightClick={onInsightClick} />
        ))}
      </div>
    </Card>
  );
}
