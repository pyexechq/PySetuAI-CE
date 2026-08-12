"use client";

import { Coins, Route, Wrench, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { CompoundingCostSummary } from "@/lib/types/domain";
import { formatNumber } from "@/lib/utils";

const ICONS = {
  compression: Zap,
  tools: Wrench,
  routing: Route,
} as const;

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function CompoundingCostCard({ data }: { data?: CompoundingCostSummary | null }) {
  const layers = data?.layers ?? [];
  const totalUsd = data?.total_estimated_usd ?? 0;
  const totalTokens = data?.total_tokens_saved ?? 0;

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Coins className="h-4 w-4 text-emerald-400" />
          Compounding cost savings
        </CardTitle>
        <CardDescription>
          Stacked estimate from cheaper routing, dynamic MCP tool ranking, and JSON/markdown compression.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          {layers.map((layer) => {
            const Icon = ICONS[layer.id as keyof typeof ICONS] ?? Coins;
            return (
              <div key={layer.id} className="rounded-lg border border-border/60 bg-muted/10 px-3 py-2.5">
                <div className="mb-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <Icon className="h-3.5 w-3.5" />
                  {layer.label}
                </div>
                <p className="text-lg font-semibold tabular-nums">{formatUsd(layer.estimated_usd)}</p>
                <p className="mt-0.5 text-[10px] text-muted-foreground">
                  {formatNumber(layer.tokens_saved)} tok · {layer.share_pct.toFixed(1)}% of stack
                </p>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted/40">
                  <div
                    className="h-full rounded-full bg-emerald-500/80 transition-[width] duration-300 ease-in-out"
                    style={{ width: `${Math.min(100, layer.share_pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg border border-border/60 px-3 py-2.5">
          <p className="text-sm text-muted-foreground">Stacked total</p>
          <p className="text-xl font-semibold tabular-nums">
            {formatUsd(totalUsd)}{" "}
            <span className="text-sm font-normal text-muted-foreground">· {formatNumber(totalTokens)} tokens avoided</span>
          </p>
        </div>
        {data?.narrative ? <p className="text-xs text-muted-foreground">{data.narrative}</p> : null}
      </CardContent>
    </Card>
  );
}
