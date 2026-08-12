"use client";

import Link from "next/link";
import { ArrowRight, Coins, Gauge, Percent, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { ApiDashboardOverview } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

type TokenSavingCardProps = {
  data?: ApiDashboardOverview["token_saving"];
};

function formatCompactTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return formatNumber(value);
}

export function TokenSavingCard({ data }: TokenSavingCardProps) {
  const original = data?.original_tokens ?? 0;
  const compressed = data?.compressed_tokens ?? 0;
  const saved = data?.tokens_saved ?? 0;
  const pct = data?.savings_pct ?? 0;
  const requests = data?.requests_compressed ?? 0;
  const hasData = original > 0;
  const compressedWidth = hasData ? Math.max(8, Math.round((compressed / original) * 100)) : 0;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 pb-3">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Zap className="h-4 w-4 text-emerald-400" />
            Token saving
          </CardTitle>
          <CardDescription>
            Before/after ingress compression (JSON→TOON and markdown strip) over the last 30 days.
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5" asChild>
          <Link href="/settings/gateway">
            Configure
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {!hasData ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No compressed requests yet. Enable token saving in Gateway settings to measure savings.
          </p>
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <MetricTile icon={Gauge} label="Before" value={formatCompactTokens(original)} hint="Original prompt tokens" />
              <MetricTile icon={Coins} label="After" value={formatCompactTokens(compressed)} hint="Tokens sent upstream" />
              <MetricTile icon={Zap} label="Saved" value={formatCompactTokens(saved)} hint={`${formatNumber(requests)} compressed requests`} />
              <MetricTile icon={Percent} label="Reduction" value={`${pct.toFixed(1)}%`} hint="Tenant-wide savings" />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span>Before</span>
                <span className="tabular-nums">{formatNumber(original)} tok</span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-muted/40">
                <div className="h-full w-full rounded-full bg-slate-500/70" />
              </div>
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span>After</span>
                <span className="tabular-nums">{formatNumber(compressed)} tok</span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-muted/40">
                <div
                  className="h-full rounded-full bg-emerald-500/80 transition-[width] duration-300 ease-in-out"
                  style={{ width: `${compressedWidth}%` }}
                />
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function MetricTile({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5">
      <div className="mb-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
      <p className="mt-0.5 text-[10px] text-muted-foreground">{hint}</p>
    </div>
  );
}
