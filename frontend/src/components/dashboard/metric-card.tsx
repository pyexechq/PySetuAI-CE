import { cn, formatNumber, formatCurrency } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { type LucideIcon, TrendingUp, TrendingDown } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  change: number;
  icon: LucideIcon;
  iconColor?: string;
  format?: "number" | "currency" | "percent" | "raw";
  periodLabel?: string;
  invertTrend?: boolean;
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
    <Card className="border-border/60 bg-card/50">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
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
