"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ArrowRightLeft, Settings2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const UNSUPPORTED_FEATURES = ["Tool calling parity", "Structured outputs", "Streaming edge cases", "Reasoning models"];

export function CompatibilityCenterView() {
  const token = useAuthStore((s) => s.token);

  const { data: stats } = useQuery({
    queryKey: ["uag-stats", token],
    queryFn: () => api.getUagStats(token!),
    enabled: Boolean(token),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Compatibility Center</h1>
          <p className="text-sm text-muted-foreground">
            Universal AI Gateway — translation stats and route compatibility. Manage mappings and policies in Settings.
          </p>
        </div>
        <Button variant="default" size="sm" className="gap-1.5" asChild>
          <Link href="/settings/uag">
            <Settings2 className="h-4 w-4" />
            Manage mappings & policies
          </Link>
        </Button>
      </div>

      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <ArrowRightLeft className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="font-medium">UAG administration</p>
              <p className="text-sm text-muted-foreground">
                Enable, disable, and delete provider mappings and translation policies from Settings → Universal AI Gateway.
              </p>
            </div>
          </div>
          <Button variant="outline" className="gap-2" asChild>
            <Link href="/settings/uag">
              Open UAG settings
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Total translations" value={String(stats?.total_translations ?? 0)} />
        <StatCard label="Success rate" value={`${Math.round((stats?.success_rate ?? 1) * 100)}%`} />
        <StatCard label="Failed" value={String(stats?.failed_translations ?? 0)} />
        <StatCard label="Avg latency" value={`${Math.round(stats?.avg_latency_ms ?? 0)} ms`} />
      </div>

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="text-base">Compatibility scores</CardTitle>
          <CardDescription>Estimated feature parity for protocol translation routes.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(stats?.compatibility_scores ?? { "openai → gemini": 0.98, "openai → claude": 0.96 }).map(
            ([route, score]) => (
              <div key={route} className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2">
                <span className="text-sm">{route}</span>
                <Badge variant="outline">{Math.round(Number(score) * 100)}%</Badge>
              </div>
            )
          )}
          {Object.entries(stats?.route_breakdown ?? {}).map(([route, count]) => (
            <div key={`usage-${route}`} className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{route}</span>
              <span>{count} events</span>
            </div>
          ))}
          <div className="pt-2">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Unsupported / partial features</p>
            <div className="flex flex-wrap gap-2">
              {UNSUPPORTED_FEATURES.map((feature) => (
                <Badge key={feature} variant="warning">
                  {feature}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="border-border/60">
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}
